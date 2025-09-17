using UnityEngine;
using System.Collections.Generic;
using System.Linq;
#if UNITY_EDITOR
using UnityEditor;
#endif

[RequireComponent(typeof(Rigidbody))]
public class BoatAI_ClusterBased : MonoBehaviour
{
    public float speed = 5f;
    public float rotationSpeed = 5f;
    public float obstacleAvoidanceRadius = 5f;
    public LayerMask obstacleLayer;

    public string algorithmName = "Greedy";
    private string initialAlgorithmName; //  유저 입력값 저장용

    private Rigidbody rb;
    public float clusterArrivalThreshold = 0.8f;
    private TrashCluster currentCluster;
    private List<TrashCluster> allClusters;
    private int currentClusterIndex = -1;

    private enum State { Idle, Navigating, Collecting, Done }
    private State currentState = State.Idle;

    private List<Vector3> zigzagPoints = new();
    public static Dictionary<TrashCluster, int> clusterCollected = new();

    private LogManager logger;
    private int obstacleCollisionCount = 0;

    private HashSet<Collider> passedObstacles = new();

    private float totalDistance = 0f;
    private Vector3 lastPosition;
    private float startTime;
    private int earlyCollectedCount = 0;




    void Start()
    {
        rb = GetComponent<Rigidbody>();
        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();
        allClusters = spawner.clusters.ToList();

        initialAlgorithmName = algorithmName;

        logger = FindObjectOfType<LogManager>();
        logger?.Log("시뮬레이션 시작", transform.position);
        logger?.Log($"알고리즘 사용됨: {algorithmName}", transform.position);
        logger?.Log($"[설정] Speed: {speed}, Rotation Speed: {rotationSpeed}, Avoid Radius: {obstacleAvoidanceRadius}, Cluster Arrival Threshold: {clusterArrivalThreshold}, Obstacle Layer: {LayerMask.LayerToName(obstacleLayer.value)}", transform.position);

        startTime = Time.time;  //  시작 시간 기록
        lastPosition = transform.position;  // 거리 측정 시작점
        GoToNextCluster();
    }


    void FixedUpdate()
    {
        VisitedGridSystem.Instance?.MarkVisited(transform.position);

        //  이동 거리 측정
        float moved = Vector3.Distance(transform.position, lastPosition);
        totalDistance += moved;
        lastPosition = transform.position;

        switch (currentState)
        {
            case State.Navigating:
                NavigateTo(currentCluster.center);
                float distToCluster = Vector3.Distance(transform.position, currentCluster.center);
                if (distToCluster < currentCluster.radius * clusterArrivalThreshold)
                {
                    logger?.Log($"클러스터 {currentCluster.name} 도착", transform.position);
                    EnterCollectionMode();
                }
                break;

            case State.Collecting:
                FollowZigZagPath();
                break;

            case State.Done:
                rb.velocity = Vector3.zero;
                break;
        }
    }


    TrashCluster ObstacleAwareSelect(Vector3 pos, out string subAlgorithmName)
    {
        subAlgorithmName = "ObstacleAware";
        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();

        TrashCluster bestCluster = null;
        float bestScore = float.MaxValue;
        string reasonLog = "";

        foreach (var cluster in allClusters)
        {
            if (clusterCollected.ContainsKey(cluster)) continue;

            float distance = Vector3.Distance(pos, cluster.center);
            int obstacleCount = Physics.OverlapSphere(cluster.center, 5f, obstacleLayer).Length;

            float score = distance + obstacleCount * 5f;

            if (score < bestScore)
            {
                bestScore = score;
                bestCluster = cluster;
                reasonLog = $"[선택 이유: {cluster.name}] 거리: {distance:F1}, 장애물 수: {obstacleCount}, 최종 점수: {score:F2}";
            }
        }

        if (bestCluster != null)
            logger?.Log(reasonLog, pos);

        return bestCluster;
    }



    void GoToNextCluster()
    {
if (clusterCollected.Keys.Count >= allClusters.Count)
{
    currentState = State.Done;
    logger?.Log("모든 클러스터 수거 완료", transform.position);
    ShowClusterStats();
    logger?.Log($"장애물 충돌 횟수: {obstacleCollisionCount}", transform.position);
    logger?.Log($"총 이동 거리: {totalDistance:F2}m", transform.position);

    SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();
    int totalTrashCount = spawner.clusterTrashCount.Values.Sum();
    float earlyPercent = totalTrashCount == 0 ? 0f : (float)earlyCollectedCount / totalTrashCount * 100f;
    logger?.Log($"2분 이내 수거 비율: {earlyPercent:F1}% ({earlyCollectedCount} / {totalTrashCount})", transform.position);

    logger?.SaveToCSV(algorithmName);
    return;
}


        Vector3 myPos = transform.position;
        string selectedAlgoDetail = "";

        //  알고리즘: Predictive 고정
        TrashCluster selected = null;

        if (algorithmName == "Greedy")
            selected = ObstacleAwareSelect(transform.position, out selectedAlgoDetail);
        else if (algorithmName == "Predictive")
            selected = PredictiveSelect(transform.position, out selectedAlgoDetail);
        else if (algorithmName == "Fusion")
            selected = FusionSelect(transform.position, out selectedAlgoDetail);
        else if (algorithmName == "Score")
            selected = ScoreSelect(transform.position, out selectedAlgoDetail);


        if (selected == null)
        {
            currentState = State.Done;
            logger?.Log("선택 가능한 클러스터 없음", transform.position);
            ShowClusterStats();
            logger?.SaveToCSV(algorithmName);
            return;
        }

        //  수거 순서 로깅 (이전 → 새 클러스터)
        if (currentCluster != null)
        {
            logger?.Log($"클러스터 {currentCluster.name} → {selected.name}", transform.position);
        }

        currentCluster = selected;
        logger?.Log($"알고리즘 사용됨: {algorithmName}", myPos);
        currentState = State.Navigating;
        logger?.Log($"클러스터 {currentCluster.name}로 이동 시작", transform.position);
    }

    TrashCluster PredictiveSelect(Vector3 pos, out string subAlgorithmName)
    {
        subAlgorithmName = "";
        int K = 5;  // 후보 클러스터 수
        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();

        // 아직 수거하지 않은 클러스터 후보들
        var candidates = allClusters.Where(c => !clusterCollected.ContainsKey(c))
                                    .OrderBy(c => Vector3.Distance(pos, c.center))
                                    .Take(K)
                                    .ToList();

        if (candidates.Count == 0) return null;

        TrashCluster bestCluster = null;
        float bestScore = float.MaxValue;
        string reasonLog = "";

        foreach (var cluster in candidates)
        {
            float distance = Vector3.Distance(pos, cluster.center);

            int trashCount = spawner.clusterTrashCount.ContainsKey(cluster) ? spawner.clusterTrashCount[cluster] : 0;
            int nearbyClusters = allClusters.Count(c => c != cluster && Vector3.Distance(cluster.center, c.center) < 10f && !clusterCollected.ContainsKey(c));
            int obstacleCount = Physics.OverlapSphere(cluster.center, 5f, obstacleLayer).Length;

            // Predictive score 계산 (임의 가중치)
            float score = distance * 1.0f - trashCount * 2.0f - nearbyClusters * 1.5f + obstacleCount * 3.0f;

            if (score < bestScore)
            {
                bestScore = score;
                bestCluster = cluster;

                reasonLog = $"[선택 이유: {cluster.name}] 거리: {distance:F1}, 쓰레기 수: {trashCount}, 주변 클러스터: {nearbyClusters}, 장애물 수: {obstacleCount}, 최종 점수: {score:F2}";
            }
        }

        if (bestCluster != null)
            logger?.Log(reasonLog, pos);

        return bestCluster;
    }
    TrashCluster FusionSelect(Vector3 pos, out string subAlgorithmName)
    {
        subAlgorithmName = "Fusion";
        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();
        var trashObjects = GameObject.FindGameObjectsWithTag("Trash");

        float bestScore = float.MaxValue;
        TrashInfo bestTrashInfo = null;

        foreach (var trash in trashObjects)
        {
            TrashInfo info = trash.GetComponent<TrashInfo>();
            if (info == null || clusterCollected.ContainsKey(info.cluster)) continue;

            Vector3 target = trash.transform.position;

            // === 경로 추정: 장애물 회피를 고려한 거리 측정 ===
            float pathLength = EstimateDirectPathLength(pos, target);
            if (pathLength < 0) continue;

            // === 장애물 밀집도 계산 (3m 이내) ===
            int obstacleCount = Physics.OverlapSphere(target, 3f, obstacleLayer).Length;

            // === 점수 계산 ===
            float score = pathLength + obstacleCount * 3f;

            if (score < bestScore)
            {
                bestScore = score;
                bestTrashInfo = info;
            }
        }

        if (bestTrashInfo != null)
        {
            logger?.Log($"Fusion 선택: {bestTrashInfo.cluster.name}, 예상 경로 길이: {bestScore - 3f * Physics.OverlapSphere(bestTrashInfo.transform.position, 3f, obstacleLayer).Length:F1}, 장애물 보정 포함 점수: {bestScore:F1}", pos);
            return bestTrashInfo.cluster;
        }

        return null;
    }


    float EstimateDirectPathLength(Vector3 start, Vector3 goal)
    {
        Vector3 dir = (goal - start).normalized;
        float totalDist = Vector3.Distance(start, goal);
        float sampledDist = 0f;
        int sampleCount = Mathf.CeilToInt(totalDist / 1f);
        Vector3 current = start;

        for (int i = 0; i < sampleCount; i++)
        {
            current += dir * 1f;
            sampledDist += 1f;

            if (Physics.CheckSphere(current, 0.5f, obstacleLayer))
            {
                return -1f; // 장애물에 막힌 경로
            }
        }

        return sampledDist;
    }




    TrashCluster ScoreSelect(Vector3 pos, out string subAlgorithmName)
    {
        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();

        float weightDistance = 0.4f;
        float weightTrashCount = -1.2f;
        float weightObstacleCount = 2.0f;
        float weightNearbyClusters = -1.0f;

        TrashCluster bestCluster = null;
        float bestScore = float.MaxValue;
        string reasonLog = "";
        subAlgorithmName = "Score";

        foreach (var cluster in allClusters)
        {
            if (clusterCollected.ContainsKey(cluster)) continue;

            float distance = Vector3.Distance(pos, cluster.center);
            int trashCount = spawner.clusterTrashCount.ContainsKey(cluster) ? spawner.clusterTrashCount[cluster] : 0;
            int obstacleCount = Physics.OverlapSphere(cluster.center, 5f, obstacleLayer).Length;
            int nearbyClusters = allClusters.Count(c => c != cluster && Vector3.Distance(cluster.center, c.center) < 10f && !clusterCollected.ContainsKey(c));

            float score = weightDistance * distance +
                          weightTrashCount * trashCount +
                          weightObstacleCount * obstacleCount +
                          weightNearbyClusters * nearbyClusters;

            if (score < bestScore)
            {
                bestScore = score;
                bestCluster = cluster;
                reasonLog = $"[선택 이유: {cluster.name}] 거리: {distance:F1}, 쓰레기 수: {trashCount}, 장애물 수: {obstacleCount}, 주변 클러스터: {nearbyClusters}, 최종 점수: {score:F2}";
            }
        }

        if (bestCluster != null)
            logger?.Log(reasonLog, pos);

        return bestCluster;
    }


    void EnterCollectionMode()
    {
        currentState = State.Collecting;
        GenerateZigZagPath();
        logger?.Log($"클러스터 {currentCluster.name} 수거 시작", transform.position);
    }

    void NavigateTo(Vector3 target)
    {
        Vector3 toTarget = (target - transform.position).normalized;
        Vector3 avoidance = AvoidObstacles();
        Vector3 finalDir = (toTarget + avoidance).normalized;

        rb.MovePosition(rb.position + finalDir * speed * Time.fixedDeltaTime);

        if (finalDir != Vector3.zero)
        {
            Quaternion rot = Quaternion.LookRotation(finalDir, Vector3.up);
            rb.MoveRotation(Quaternion.Slerp(rb.rotation, rot, rotationSpeed * Time.fixedDeltaTime));
        }
    }

    Vector3 AvoidObstacles()
    {
        Vector3 avoid = Vector3.zero;
        Collider[] hits = Physics.OverlapSphere(transform.position, obstacleAvoidanceRadius);

        foreach (Collider hit in hits)
        {
            if (passedObstacles.Contains(hit)) continue;

            if (((1 << hit.gameObject.layer) & obstacleLayer) != 0)
            {
                Vector3 away = transform.position - hit.ClosestPoint(transform.position);
                float dist = away.magnitude;

                if (dist < 1f) continue; // 너무 가까우면 무시

                // 힘 제한: 0.5보다 크게 못하게 조정
                float strength = Mathf.Clamp(hit.CompareTag("Obstacle") ? 1f / dist : 0.3f / dist, 0f, 0.5f);
                avoid += away.normalized * strength;
            }
        }

        return avoid.normalized;
    }


    void GenerateZigZagPath()
    {
        zigzagPoints.Clear();

        int lineCount = Mathf.Max(4, Mathf.FloorToInt(currentCluster.radius / 2f));
        float spacing = currentCluster.radius * 2f / (lineCount - 1);
        float forwardLength = currentCluster.radius * 1.5f;

        Vector3 forwardStart = currentCluster.center - transform.forward * (forwardLength / 2f);
        bool leftToRight = true;

        for (int i = 0; i < lineCount; i++)
        {
            float offset = -currentCluster.radius + spacing * i;
            Vector3 side = transform.right * offset;
            Vector3 start = forwardStart + side;
            Vector3 end = start + transform.forward * forwardLength;

            if (!leftToRight)
            {
                var temp = start;
                start = end;
                end = temp;
            }

            zigzagPoints.Add(start);
            zigzagPoints.Add(end);
            leftToRight = !leftToRight;
        }
    }

void FollowZigZagPath()
{
    if (zigzagPoints.Count == 0)
    {
        logger?.Log($"클러스터 {currentCluster.name} 수거 완료", transform.position);
        clusterCollected[currentCluster] = clusterCollected.ContainsKey(currentCluster)
            ? clusterCollected[currentCluster]
            : 0;
        GoToNextCluster();
        return;
    }

    // 현재 타겟 지점
    Vector3 target = zigzagPoints[0];
    Vector3 dir = (target - transform.position).normalized;

    // 꺾이는 지점을 감지할 거리 (1m 안쪽을 'turning area'로 본다)
    const float cornerThreshold = 1f;
    bool atCorner = Vector3.Distance(transform.position, target) < cornerThreshold;

    // 코너가 아니면 회피 적용, 코너 안이면 회피 벡터를 0으로
    Vector3 avoidance = atCorner
        ? Vector3.zero
        : AvoidObstacles();

    // 최종 이동 방향
    Vector3 finalDir = (dir + avoidance).normalized;

    // 이동
    rb.MovePosition(rb.position + finalDir * speed * Time.fixedDeltaTime);

    // 회전 (꺾일 때도 자연스럽게 방향 전환)
    Quaternion rot = Quaternion.LookRotation(finalDir, Vector3.up);
    rb.MoveRotation(Quaternion.Slerp(rb.rotation, rot, rotationSpeed * Time.fixedDeltaTime));

    // 목표 지점 도달 시 다음 포인트로
    if (Vector3.Distance(transform.position, target) < cornerThreshold)
    {
        zigzagPoints.RemoveAt(0);
    }
}


    void OnTriggerEnter(Collider other)
    {
        // 쓰레기만 처리
        if (!other.CompareTag("Trash"))
        {
            // 장애물 충돌만 기록
            if (((1 << other.gameObject.layer) & obstacleLayer) != 0)
            {
                if (!passedObstacles.Contains(other))
                {
                    obstacleCollisionCount++;
                    passedObstacles.Add(other);
                    logger?.Log($"장애물 트리거 충돌: {other.gameObject.name}", transform.position);
                }
            }
            return;
        }

        // TrashInfo 가져오기
        TrashInfo info = other.GetComponent<TrashInfo>();
        // 목적 클러스터 쓰레기 아니면 무시
        if (info == null || info.cluster != currentCluster)
            return;

        // 이미 수거한 적이 없으면 카운트
        if (!clusterCollected.ContainsKey(currentCluster))
            clusterCollected[currentCluster] = 0;

        if (!other.gameObject.TryGetComponent<AlreadyCollected>(out _))
        {
            clusterCollected[currentCluster]++;
            other.gameObject.AddComponent<AlreadyCollected>();

            // 2분 이내 수거 기록
            if (Time.time - startTime <= 120f)
                earlyCollectedCount++;
        }

        Destroy(other.gameObject);
    }



    void ShowClusterStats()
    {
        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();
        if (spawner == null || spawner.clusterTrashCount == null) return;

        foreach (var cluster in spawner.clusters)
        {
            int total = spawner.clusterTrashCount.ContainsKey(cluster) ? spawner.clusterTrashCount[cluster] : 0;
            int collected = clusterCollected.ContainsKey(cluster) ? clusterCollected[cluster] : 0;
            float rate = total == 0 ? 0f : (float)collected / total * 100f;

            string statLine = $"클러스터 {cluster.name} 수거율: {rate:F1}%";
            Debug.Log(statLine);
            logger?.Log(statLine, transform.position);
        }
    }

    void OnApplicationQuit()
    {
        logger?.Log("시뮬레이션 강제 종료됨", transform.position);
        logger?.Log($"총 이동 거리: {totalDistance:F2}m", transform.position);

        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();
        int totalTrashCount = spawner.clusterTrashCount.Values.Sum();
        float earlyPercent = totalTrashCount == 0 ? 0f : (float)earlyCollectedCount / totalTrashCount * 100f;
        logger?.Log($"2분 이내 수거 비율: {earlyPercent:F1}% ({earlyCollectedCount} / {totalTrashCount})", transform.position);

        logger?.Log($"장애물 충돌 횟수: {obstacleCollisionCount}", transform.position);
        logger?.SaveToCSV(initialAlgorithmName);
    }



}

public class AlreadyCollected : MonoBehaviour { }


