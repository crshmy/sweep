using UnityEngine;

[System.Serializable]
public class TrashCluster
{
    public string name;
    public Vector3 center;
    public float radius = 5f;
    public int count = 20;
    public Color gizmoColor = Color.red;
}
