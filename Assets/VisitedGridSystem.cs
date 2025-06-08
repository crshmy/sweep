using UnityEngine;

public class VisitedGridSystem : MonoBehaviour
{
    public static VisitedGridSystem Instance;

    public int gridSize = 100;
    public float cellSize = 1f;
    private bool[,] visited;

    void Awake()
    {
        Instance = this;
        visited = new bool[gridSize, gridSize];
    }

    public void MarkVisited(Vector3 position)
    {
        int x = Mathf.FloorToInt(position.x + gridSize / 2);
        int z = Mathf.FloorToInt(position.z + gridSize / 2);

        if (x >= 0 && x < gridSize && z >= 0 && z < gridSize)
        {
            visited[x, z] = true;
        }
    }

    void OnDrawGizmos()
    {
        if (visited == null) return;

        Gizmos.color = new Color(1f, 1f, 0f, 0.25f); // ¹ÝÅõ¸í ³ë¶û

        for (int x = 0; x < gridSize; x++)
        {
            for (int z = 0; z < gridSize; z++)
            {
                if (visited[x, z])
                {
                    Vector3 pos = new Vector3(x - gridSize / 2 + 0.5f, 0f, z - gridSize / 2 + 0.5f);
                    Gizmos.DrawCube(pos, Vector3.one * cellSize);
                }
            }
        }
    }
}
