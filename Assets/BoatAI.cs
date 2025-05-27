using UnityEngine;
using System.Collections.Generic;
using System.Linq;

[RequireComponent(typeof(Rigidbody))]
public class BoatAI : MonoBehaviour
{
    public float speed = 5f;
    private Rigidbody rb;
    private EvaluationManager eval;

    private List<Vector3> path = new List<Vector3>();
    private int currentPathIndex = 0;
    private float reachThreshold = 0.5f;

    private List<GameObject> trashObjects;
    private List<Vector3> trashPositions;
    private List<Vector3> obstaclePositions;

    void Start()
    {
        rb = GetComponent<Rigidbody>();
        eval = FindObjectOfType<EvaluationManager>();

        RecalculateFusionPath(); // 최초 경로 계산
    }

    void FixedUpdate()
    {
        if (path.Count == 0 || currentPathIndex >= path.Count)
        {
            RecalculateFusionPath();
            return;
        }

        Vector3 targetPos = path[currentPathIndex];
        Vector3 dir = (targetPos - transform.position).normalized;
        rb.MovePosition(rb.position + dir * speed * Time.fixedDeltaTime);
        Quaternion rot = Quaternion.LookRotation(dir);
        rb.MoveRotation(Quaternion.Slerp(rb.rotation, rot, 5f * Time.fixedDeltaTime));

        if (Vector3.Distance(transform.position, targetPos) < reachThreshold)
        {
            currentPathIndex++;
        }
    }

    void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Trash"))
        {
            if (eval != null)
            {
                eval.TrashCollected(other.gameObject);
            }

            Destroy(other.gameObject);
            RecalculateFusionPath(); // 수거 후 경로 갱신
        }
    }

    void RecalculateFusionPath()
    {
        trashObjects = GameObject.FindGameObjectsWithTag("Trash").ToList();
        trashPositions = trashObjects.Select(t => RoundToGrid(t.transform.position)).ToList();

        obstaclePositions = GameObject.FindGameObjectsWithTag("Obstacle")
            .Select(o => RoundToGrid(o.transform.position)).ToList();

        path.Clear();
        currentPathIndex = 0;

        if (trashPositions.Count == 0)
        {
            if (eval != null && !eval.hasSaved)
            {
                eval.SaveResults();
                Debug.Log("모든 쓰레기 수거 완료");
            }
            enabled = false;
            return;
        }

        Vector3 start = RoundToGrid(transform.position);
        HashSet<Vector3> collected = new HashSet<Vector3>();

        int maxIterations = 100;
        for (int i = 0; i < maxIterations && trashPositions.Count > 0; i++)
        {
            Vector3 target = trashPositions.OrderBy(p => Vector3.Distance(start, p)).First();
            List<Vector3> newPath = AStar(start, target);

            if (newPath == null || newPath.Count == 0)
            {
                newPath = Dijkstra(start, target);
            }

            if (newPath != null && newPath.Count > 0)
            {
                path.AddRange(newPath.Skip(1));
                start = newPath.Last();
                collected.Add(target);
            }

            trashPositions = trashPositions.Where(p => !collected.Contains(p)).ToList();
        }
    }

    List<Vector3> AStar(Vector3 start, Vector3 goal)
    {
        var open = new PriorityQueue<Vector3>();
        var cameFrom = new Dictionary<Vector3, Vector3>();
        var gScore = new Dictionary<Vector3, float> { [start] = 0 };

        open.Enqueue(start, Vector3.Distance(start, goal));

        while (open.Count > 0)
        {
            Vector3 current = open.Dequeue();
            if (Vector3.Distance(current, goal) < 0.5f)
                return ReconstructPath(cameFrom, current);

            foreach (Vector3 neighbor in GetNeighbors(current))
            {
                if (IsObstacle(neighbor)) continue;

                float tentative = gScore[current] + Vector3.Distance(current, neighbor);
                if (!gScore.ContainsKey(neighbor) || tentative < gScore[neighbor])
                {
                    cameFrom[neighbor] = current;
                    gScore[neighbor] = tentative;
                    open.Enqueue(neighbor, tentative + Vector3.Distance(neighbor, goal));
                }
            }
        }
        return null;
    }

    List<Vector3> Dijkstra(Vector3 start, Vector3 goal)
    {
        var open = new PriorityQueue<Vector3>();
        var cameFrom = new Dictionary<Vector3, Vector3>();
        var cost = new Dictionary<Vector3, float> { [start] = 0 };

        open.Enqueue(start, 0);

        while (open.Count > 0)
        {
            Vector3 current = open.Dequeue();
            if (Vector3.Distance(current, goal) < 0.5f)
                return ReconstructPath(cameFrom, current);

            foreach (Vector3 neighbor in GetNeighbors(current))
            {
                if (IsObstacle(neighbor)) continue;

                float newCost = cost[current] + 1;
                if (!cost.ContainsKey(neighbor) || newCost < cost[neighbor])
                {
                    cost[neighbor] = newCost;
                    cameFrom[neighbor] = current;
                    open.Enqueue(neighbor, newCost);
                }
            }
        }
        return null;
    }

    List<Vector3> ReconstructPath(Dictionary<Vector3, Vector3> cameFrom, Vector3 current)
    {
        var totalPath = new List<Vector3> { current };
        while (cameFrom.ContainsKey(current))
        {
            current = cameFrom[current];
            totalPath.Insert(0, current);
        }
        return totalPath;
    }

    List<Vector3> GetNeighbors(Vector3 pos)
    {
        int x = Mathf.RoundToInt(pos.x);
        int z = Mathf.RoundToInt(pos.z);

        return new List<Vector3> {
            new Vector3(x + 1, 0, z),
            new Vector3(x - 1, 0, z),
            new Vector3(x, 0, z + 1),
            new Vector3(x, 0, z - 1)
        };
    }

    bool IsObstacle(Vector3 pos)
    {
        Vector3 rounded = RoundToGrid(pos);
        return obstaclePositions.Contains(rounded);
    }

    Vector3 RoundToGrid(Vector3 pos)
    {
        return new Vector3(
            Mathf.Round(pos.x),
            0,
            Mathf.Round(pos.z)
        );
    }

    public class PriorityQueue<T>
    {
        private List<(float, T)> elements = new List<(float, T)>();
        public int Count => elements.Count;
        public void Enqueue(T item, float priority)
        {
            elements.Add((priority, item));
            elements.Sort((a, b) => a.Item1.CompareTo(b.Item1));
        }
        public T Dequeue()
        {
            var item = elements[0];
            elements.RemoveAt(0);
            return item.Item2;
        }
    }
}
