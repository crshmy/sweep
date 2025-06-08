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

    private Rigidbody rb;
    public float clusterArrivalThreshold = 0.8f;
    private TrashCluster currentCluster;
    private List<TrashCluster> allClusters;
    private int currentClusterIndex = -1;

    private enum State { Idle, Navigating, Collecting, Done }
    private State currentState = State.Idle;

    private List<Vector3> zigzagPoints = new List<Vector3>();

    public static Dictionary<TrashCluster, int> clusterCollected = new();

    void Start()
    {
        rb = GetComponent<Rigidbody>();
        SmartTrashSpawner spawner = FindObjectOfType<SmartTrashSpawner>();
        allClusters = spawner.clusters.ToList();
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
        currentClusterIndex++;
        if (currentClusterIndex >= allClusters.Count)
        {
            currentState = State.Done;
            Debug.Log("모든 클러스터 수거 완료");
            ShowClusterStats();
            return;
        }

        currentCluster = allClusters[currentClusterIndex];
        currentState = State.Navigating;
        Debug.Log("다음 클러스터 이동: " + currentCluster.name);
    }

    void EnterCollectionMode()
    {
        currentState = State.Collecting;
        GenerateZigZagPath();
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
            if (((1 << hit.gameObject.layer) & obstacleLayer) != 0)
            {
                Vector3 away = transform.position - hit.ClosestPoint(transform.position);
                float dist = away.magnitude;

                if (dist > 0)
                {
                    float strength = hit.CompareTag("StaticObstacle") ? 1f : 0.3f;
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
            GoToNextCluster();
            return;
        }

        Vector3 target = zigzagPoints[0];
        Vector3 dir = (target - transform.position).normalized;
        rb.MovePosition(rb.position + dir * speed * Time.fixedDeltaTime);

        Quaternion rot = Quaternion.LookRotation(dir, Vector3.up);
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
            Debug.Log($"클러스터 {cluster.name} 수거율: {rate:F1}%");
        }
    }
}

public class AlreadyCollected : MonoBehaviour {}
