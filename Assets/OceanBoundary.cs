using UnityEngine;

public class OceanBoundaryGizmo : MonoBehaviour
{
    public Vector2 size = new Vector2(50, 50);
    public Color gizmoColor = Color.cyan;

    void OnDrawGizmos()
    {
        Gizmos.color = gizmoColor;
        Gizmos.DrawWireCube(Vector3.zero, new Vector3(size.x, 0.1f, size.y));
    }
}
