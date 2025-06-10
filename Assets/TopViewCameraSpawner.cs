using UnityEngine;
using Cinemachine;

public class TopViewCameraSpawner : MonoBehaviour
{
    public GameObject cameraPrefab; // CinemachineVirtualCamera 프리팹
    public float heightAboveCluster = 50f;

    void Start()
    {
        var spawner = FindObjectOfType<SmartTrashSpawner>();
        if (spawner == null || spawner.clusters == null || spawner.clusters.Length == 0) return;

        for (int i = 0; i < spawner.clusters.Length; i++)
        {
            var cluster = spawner.clusters[i];

            // 카메라 생성
            GameObject camObj = Instantiate(cameraPrefab);
            camObj.name = $"ClusterCam_{cluster.name}";
            camObj.transform.position = cluster.center + new Vector3(0f, heightAboveCluster, 0f);

            // LookAt용 임시 타겟 오브젝트 생성
            GameObject target = new GameObject($"ClusterTarget_{cluster.name}");
            target.transform.position = cluster.center;

            var cam = camObj.GetComponent<CinemachineVirtualCamera>();
            if (cam != null)
            {
                cam.LookAt = target.transform;
                cam.Priority = 0; // 기본은 꺼짐 상태
            }
        }
    }
}
