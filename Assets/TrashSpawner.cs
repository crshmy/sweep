using UnityEngine;
using System.Collections.Generic;

#if UNITY_EDITOR
using UnityEditor;  // Gizmo에 텍스트 Label 표시용
#endif

public class SmartTrashSpawner : MonoBehaviour
{
    [Header(" 쓰레기 프리팹")]
    public GameObject[] trashPrefabs;

    [Header(" 쓰레기 밀집 클러스터 설정")]
    public TrashCluster[] clusters;

    [Header(" 전체 분산 쓰레기 설정")]
    public int dispersedTrashCount = 30;
    public Vector2 spawnAreaSize = new Vector2(50, 50);

    [Header(" 충돌 방지 설정")]
    public float overlapCheckRadius = 0.5f;
    public int maxSpawnAttemptsPerTrash = 10;

    [Header(" 위치 흔들림")]
    public float clusterJitterRange = 0.5f;

    public Dictionary<TrashCluster, int> clusterTrashCount = new();

    public static SmartTrashSpawner Instance { get; private set; }

    void Awake()
    {
        Instance = this;
    }

    void Start()
    {
        if (trashPrefabs == null || trashPrefabs.Length == 0)
        {
            Debug.LogError(" trashPrefabs가 비어 있습니다.");
            return;
        }

        SpawnClusters();
        SpawnDispersedTrash();
    }

    void SpawnClusters()
    {
        foreach (var cluster in clusters)
        {
            int spawned = 0;
            int attempts = 0;

            if (!clusterTrashCount.ContainsKey(cluster))
                clusterTrashCount[cluster] = 0;

            while (spawned < cluster.count && attempts < cluster.count * maxSpawnAttemptsPerTrash)
            {
                Vector2 offset = Random.insideUnitCircle * cluster.radius;

                float noise = Mathf.PerlinNoise(offset.x * 0.5f + 100f, offset.y * 0.5f + 100f);
                offset *= Mathf.Lerp(0.6f, 1.3f, noise);

                Vector3 pos = cluster.center + new Vector3(offset.x, 0f, offset.y);
                pos += new Vector3(Random.Range(-clusterJitterRange, clusterJitterRange), 0f, Random.Range(-clusterJitterRange, clusterJitterRange));

                if (IsPositionClear(pos))
                {
                    SpawnClusterTrash(pos, cluster);
                    spawned++;
                   
                }

                attempts++;
            }
        }
    }

    void SpawnDispersedTrash()
    {
        int spawned = 0;
        int attempts = 0;

        while (spawned < dispersedTrashCount && attempts < dispersedTrashCount * maxSpawnAttemptsPerTrash)
        {
            float x = Random.Range(-spawnAreaSize.x / 2f, spawnAreaSize.x / 2f);
            float z = Random.Range(-spawnAreaSize.y / 2f, spawnAreaSize.y / 2f);
            Vector3 pos = new Vector3(x, 0f, z);

            if (IsPositionClear(pos))
            {
                TrashCluster cluster = FindClusterForPosition(pos);

                if (cluster != null)
                {
                    SpawnClusterTrash(pos, cluster);
                    clusterTrashCount[cluster]++;
                }
                else
                {
                    SpawnRandomTrash(pos);
                }

                spawned++;
            }

            attempts++;
        }
    }

    TrashCluster FindClusterForPosition(Vector3 pos)
    {
        foreach (var c in clusters)
        {
            if (Vector3.Distance(pos, c.center) <= c.radius)
                return c;
        }
        return null;
    }

    bool IsPositionClear(Vector3 pos)
    {
        return !Physics.CheckSphere(pos + Vector3.up * 0.5f, overlapCheckRadius);
    }

    void SpawnRandomTrash(Vector3 position)
    {
        GameObject prefab = trashPrefabs[Random.Range(0, trashPrefabs.Length)];
        Quaternion randomRotation = Quaternion.Euler(Random.Range(0f, 15f), Random.Range(0f, 360f), Random.Range(0f, 15f));
        GameObject obj = Instantiate(prefab, position, randomRotation);
        obj.transform.localScale *= Random.Range(0.9f, 1.1f);

        Rigidbody rb = obj.GetComponent<Rigidbody>();
        if (rb != null)
        {
            rb.velocity = Vector3.zero;
            rb.angularVelocity = Vector3.zero;
        }

        obj.tag = "Trash";
    }

    void SpawnClusterTrash(Vector3 position, TrashCluster cluster)
    {
        GameObject prefab = trashPrefabs[Random.Range(0, trashPrefabs.Length)];
        Quaternion randomRotation = Quaternion.Euler(Random.Range(0f, 15f), Random.Range(0f, 360f), Random.Range(0f, 15f));
        GameObject obj = Instantiate(prefab, position, randomRotation);
        obj.transform.localScale *= Random.Range(0.9f, 1.1f);

        Rigidbody rb = obj.GetComponent<Rigidbody>();
        if (rb != null)
        {
            rb.velocity = Vector3.zero;
            rb.angularVelocity = Vector3.zero;
        }

        obj.tag = "Trash";

        TrashInfo info = obj.AddComponent<TrashInfo>();
        info.cluster = cluster;

        //  여기서만 카운트 증가!
        if (!clusterTrashCount.ContainsKey(cluster))
            clusterTrashCount[cluster] = 0;
        clusterTrashCount[cluster]++;
    }

    void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.cyan;
        Gizmos.DrawWireCube(Vector3.zero, new Vector3(spawnAreaSize.x, 0.1f, spawnAreaSize.y));

        if (clusters != null)
        {
            foreach (var c in clusters)
            {
                Gizmos.color = c.gizmoColor;
                Gizmos.DrawWireSphere(c.center, c.radius);

#if UNITY_EDITOR
                Handles.color = c.gizmoColor;
                Handles.Label(c.center + Vector3.up * 1.5f, c.name);
#endif
            }
        }
    }
}
