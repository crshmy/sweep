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

    void Start()
    {
        rb = GetComponent<Rigidbody>();
        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();
        allClusters = spawner.clusters.ToList();

        initialAlgorithmName = algorithmName; //  초기 설정값 저장

        logger = FindObjectOfType<LogManager>();
        logger?.Log("시뮬레이션 시작", transform.position);
        logger?.Log($"알고리즘 사용됨: {algorithmName}", transform.position);
        logger?.Log($"[설정] Speed: {speed}, Rotation Speed: {rotationSpeed}, Avoid Radius: {obstacleAvoidanceRadius}, Cluster Arrival Threshold: {clusterArrivalThreshold}, Obstacle Layer: {LayerMask.LayerToName(obstacleLayer.value)}", transform.position);

        GoToNextCluster();
    }

    void FixedUpdate()
    {
        VisitedGridSystem.Instance?.MarkVisited(transform.position);

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

    void GoToNextCluster()
    {
        if (clusterCollected.Keys.Count >= allClusters.Count)
        {
            currentState = State.Done;
            logger?.Log("모든 클러스터 수거 완료", transform.position);
            ShowClusterStats();
            logger?.Log($"장애물 충돌 횟수: {obstacleCollisionCount}", transform.position);
            logger?.SaveToCSV(initialAlgorithmName); //  유저 입력값으로 저장
            return;
        }

        Vector3 myPos = transform.position;
        TrashCluster selected = null;

        int algoIndex = clusterCollected.Count % 3;
        switch (algoIndex)
        {
            case 0:
                selected = GreedySelect(myPos);
                algorithmName = "Greedy";
                break;
            case 1:
                selected = DensitySelect(myPos);
                algorithmName = "DensityBased";
                break;
            case 2:
                selected = NearestSelect(myPos);
                algorithmName = "Nearest";
                break;
        }

        if (selected == null)
        {
            currentState = State.Done;
            logger?.Log("선택 가능한 클러스터 없음", transform.position);
            ShowClusterStats();
            logger?.SaveToCSV(initialAlgorithmName);
            return;
        }

        currentCluster = selected;
        logger?.Log($"알고리즘 사용됨: {algorithmName}", myPos);
        currentState = State.Navigating;
        logger?.Log($"클러스터 {currentCluster.name}로 이동 시작", transform.position);
    }

    TrashCluster GreedySelect(Vector3 pos)
    {
        return allClusters.Where(c => !clusterCollected.ContainsKey(c)).OrderBy(c => Vector3.Distance(pos, c.center)).FirstOrDefault();
    }

    TrashCluster DensitySelect(Vector3 pos)
    {
        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();
        return allClusters.Where(c => !clusterCollected.ContainsKey(c))
            .OrderByDescending(c => spawner.clusterTrashCount.ContainsKey(c) ? spawner.clusterTrashCount[c] : 0).FirstOrDefault();
    }

    TrashCluster NearestSelect(Vector3 pos)
    {
        return allClusters.Where(c => !clusterCollected.ContainsKey(c)).OrderBy(c => Vector3.Distance(pos, c.center)).FirstOrDefault();
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

                if (dist > 0)
                {
                    float strength = hit.CompareTag("Obstacle") ? 1f : 0.3f;
                    avoid += (away.normalized / dist) * strength;
                }
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
            clusterCollected[currentCluster] = clusterCollected.ContainsKey(currentCluster) ? clusterCollected[currentCluster] : 0;
            GoToNextCluster();
            return;
        }

        Vector3 target = zigzagPoints[0];
        Vector3 dir = (target - transform.position).normalized;
        Vector3 avoidance = AvoidObstacles();
        Vector3 finalDir = (dir + avoidance).normalized;

        rb.MovePosition(rb.position + finalDir * speed * Time.fixedDeltaTime);

        Quaternion rot = Quaternion.LookRotation(finalDir, Vector3.up);
        rb.MoveRotation(Quaternion.Slerp(rb.rotation, rot, rotationSpeed * Time.fixedDeltaTime));

        if (Vector3.Distance(transform.position, target) < 1f)
        {
            zigzagPoints.RemoveAt(0);
        }
    }

    void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Trash"))
        {
            TrashInfo info = other.GetComponent<TrashInfo>();
            if (info != null && info.cluster != null)
            {
                if (!clusterCollected.ContainsKey(info.cluster))
                    clusterCollected[info.cluster] = 0;

                if (!other.gameObject.TryGetComponent<AlreadyCollected>(out _))
                {
                    clusterCollected[info.cluster]++;
                    other.gameObject.AddComponent<AlreadyCollected>();
                }
            }

            Destroy(other.gameObject);
        }
        else if (((1 << other.gameObject.layer) & obstacleLayer) != 0 && !other.CompareTag("Trash"))
        {
            if (!passedObstacles.Contains(other))
            {
                obstacleCollisionCount++;
                passedObstacles.Add(other);
                logger?.Log($"장애물 트리거 충돌: {other.gameObject.name}", transform.position);
            }
        }
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
        logger?.Log($"장애물 충돌 횟수: {obstacleCollisionCount}", transform.position);
        logger?.SaveToCSV(initialAlgorithmName); // 유저 입력값으로 저장
    }
}

public class AlreadyCollected : MonoBehaviour { }
