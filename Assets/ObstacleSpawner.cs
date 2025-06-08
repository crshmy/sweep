using UnityEngine;
#if UNITY_EDITOR
using UnityEditor;  // Gizmo Label 표시용
#endif

public class SmartObstacleSpawner : MonoBehaviour
{
    [Header("고정 장애물 (바위 등, Rigidbody 없음)")]
    public GameObject[] staticObstacles;

    [Header("부력 장애물 (부표 등, Rigidbody + Crest 스크립트 붙은 프리팹)")]
    public GameObject[] buoyantObstacles;

    [Header("고정 장애물 클러스터")]
    public ObstacleCluster[] staticClusters;

    [Header("부력 장애물 클러스터")]
    public ObstacleCluster[] buoyantClusters;

    [Header("전체 분산 장애물 수")]
    public int dispersedStaticCount = 10;
    public int dispersedBuoyantCount = 10;

    [Header("분산 스폰 영역")]
    public Vector2 spawnAreaSize = new Vector2(50, 50);

    [Header("충돌 방지 설정")]
    public float overlapCheckRadius = 1f;
    public int maxSpawnAttemptsPerObstacle = 10;

    [Header("위치 흔들림")]
    public float jitterRange = 0.5f;

    [System.Serializable]
    public class ObstacleCluster
    {
        public string name;
        public Vector3 center;
        public float radius = 5f;
        public int count = 10;
        public Color gizmoColor = Color.gray;
    }

    void Start()
    {
        SpawnClusters(staticClusters, staticObstacles, false);
        SpawnClusters(buoyantClusters, buoyantObstacles, true);

        SpawnDispersedObstacles(staticObstacles, dispersedStaticCount, false);
        SpawnDispersedObstacles(buoyantObstacles, dispersedBuoyantCount, true);
    }

    void SpawnClusters(ObstacleCluster[] clusters, GameObject[] prefabs, bool useBuoyancy)
    {
        foreach (var cluster in clusters)
        {
            int spawned = 0;
            int attempts = 0;

            while (spawned < cluster.count && attempts < cluster.count * maxSpawnAttemptsPerObstacle)
            {
                Vector2 offset = Random.insideUnitCircle * cluster.radius;
                Vector3 pos = cluster.center + new Vector3(offset.x, 0f, offset.y);
                pos += new Vector3(Random.Range(-jitterRange, jitterRange), 0f, Random.Range(-jitterRange, jitterRange));

                if (IsPositionClear(pos))
                {
                    SpawnObstacle(prefabs, pos, useBuoyancy);
                    spawned++;
                }
                attempts++;
            }
        }
    }

    void SpawnDispersedObstacles(GameObject[] prefabs, int count, bool useBuoyancy)
    {
        int spawned = 0;
        int attempts = 0;
        while (spawned < count && attempts < count * maxSpawnAttemptsPerObstacle)
        {
            float x = Random.Range(-spawnAreaSize.x / 2f, spawnAreaSize.x / 2f);
            float z = Random.Range(-spawnAreaSize.y / 2f, spawnAreaSize.y / 2f);
            Vector3 pos = new Vector3(x, 0f, z);

            if (IsPositionClear(pos))
            {
                SpawnObstacle(prefabs, pos, useBuoyancy);
                spawned++;
            }
            attempts++;
        }
    }

    bool IsPositionClear(Vector3 pos)
    {
        return !Physics.CheckSphere(pos + Vector3.up * 0.5f, overlapCheckRadius);
    }

    void SpawnObstacle(GameObject[] prefabs, Vector3 pos, bool useBuoyancy)
    {
        GameObject prefab = prefabs[Random.Range(0, prefabs.Length)];
        GameObject obj = Instantiate(prefab, pos, Quaternion.identity);

        //  고정 장애물만 랜덤 크기 조정
        if (!useBuoyancy)
        {
            float scale = Random.Range(0.8f, 1.5f); // 너가 원하는 크기 범위로 조절
            obj.transform.localScale *= scale;

            // Rigidbody 있으면 제거
            if (obj.TryGetComponent<Rigidbody>(out Rigidbody rb))
            {
                Destroy(rb);
            }
        }
        else
        {
            // 부력용 장애물은 Rigidbody 필요
            if (!obj.TryGetComponent<Rigidbody>(out _))
            {
                obj.AddComponent<Rigidbody>();
            }
        }
    }


#if UNITY_EDITOR
    void OnDrawGizmosSelected()
    {
        DrawGizmos(staticClusters);
        DrawGizmos(buoyantClusters);
    }

    void DrawGizmos(ObstacleCluster[] clusters)
    {
        foreach (var c in clusters)
        {
            Gizmos.color = c.gizmoColor;
            Gizmos.DrawWireSphere(c.center, c.radius);
            Handles.color = c.gizmoColor;
            Handles.Label(c.center + Vector3.up * 2f, c.name);
        }
    }
#endif
}
