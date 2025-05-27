using System;
using System.Collections.Generic;
using UnityEngine;

public class SweepAlgorithm : MonoBehaviour
{
    public int gridSize = 50;
    public Vector2Int startPos;

    public List<Vector2Int> trashPositions = new List<Vector2Int>();
    public List<Vector2Int> obstaclePositions = new List<Vector2Int>();

    private HashSet<Vector2Int> collected = new HashSet<Vector2Int>();

    private void Awake()
    {
        // 태그 기반 자동 초기화
        foreach (var trash in GameObject.FindGameObjectsWithTag("Trash"))
        {
            Vector3 pos = trash.transform.position;
            trashPositions.Add(new Vector2Int(Mathf.RoundToInt(pos.x), Mathf.RoundToInt(pos.z)));
        }

        foreach (var obstacle in GameObject.FindGameObjectsWithTag("Obstacle"))
        {
            Vector3 pos = obstacle.transform.position;
            obstaclePositions.Add(new Vector2Int(Mathf.RoundToInt(pos.x), Mathf.RoundToInt(pos.z)));
        }

        startPos = new Vector2Int(Mathf.RoundToInt(transform.position.x), Mathf.RoundToInt(transform.position.z));
    }

    private float Distance(Vector2Int a, Vector2Int b)
    {
        return Vector2Int.Distance(a, b);
    }

    private bool IsCollision(Vector2Int pos)
    {
        return obstaclePositions.Contains(pos);
    }

    private List<Vector2Int> Neighbors(Vector2Int pos)
    {
        List<Vector2Int> result = new List<Vector2Int>();
        Vector2Int[] directions = {
            new Vector2Int(-1, 0),
            new Vector2Int(1, 0),
            new Vector2Int(0, -1),
            new Vector2Int(0, 1)
        };

        foreach (var dir in directions)
        {
            Vector2Int neighbor = pos + dir;
            if (neighbor.x >= 0 && neighbor.x < gridSize && neighbor.y >= 0 && neighbor.y < gridSize)
            {
                result.Add(neighbor);
            }
        }
        return result;
    }

    private List<Vector2Int> ReconstructPath(Dictionary<Vector2Int, Vector2Int> cameFrom, Vector2Int current)
    {
        List<Vector2Int> path = new() { current };
        while (cameFrom.ContainsKey(current))
        {
            current = cameFrom[current];
            path.Add(current);
        }
        path.Reverse();
        return path;
    }

    private List<Vector2Int> AStarSearch(Vector2Int start, Vector2Int goal)
    {
        var openSet = new SortedSet<(float fScore, int count, Vector2Int pos)>(Comparer<(float, int, Vector2Int)>.Create((a, b) =>
        {
            int cmp = a.fScore.CompareTo(b.fScore);
            if (cmp == 0) cmp = a.count.CompareTo(b.count);
            if (cmp == 0) cmp = a.pos.x.CompareTo(b.pos.x);
            if (cmp == 0) cmp = a.pos.y.CompareTo(b.pos.y);
            return cmp;
        }));

        int counter = 0;
        openSet.Add((Distance(start, goal), counter++, start));

        Dictionary<Vector2Int, Vector2Int> cameFrom = new();
        Dictionary<Vector2Int, float> gScore = new() { [start] = 0 };

        while (openSet.Count > 0)
        {
            var current = openSet.Min.pos;
            openSet.Remove(openSet.Min);

            if (current == goal)
                return ReconstructPath(cameFrom, current);

            foreach (var neighbor in Neighbors(current))
            {
                if (IsCollision(neighbor)) continue;

                float tentative = gScore[current] + 1;
                if (!gScore.ContainsKey(neighbor) || tentative < gScore[neighbor])
                {
                    cameFrom[neighbor] = current;
                    gScore[neighbor] = tentative;
                    openSet.Add((tentative + Distance(neighbor, goal), counter++, neighbor));
                }
            }
        }
        return null;
    }

    private List<Vector2Int> DijkstraSearch(Vector2Int start, Vector2Int goal)
    {
        var open = new SortedSet<(float cost, int count, Vector2Int pos)>(Comparer<(float, int, Vector2Int)>.Create((a, b) =>
        {
            int cmp = a.cost.CompareTo(b.cost);
            if (cmp == 0) cmp = a.count.CompareTo(b.count);
            if (cmp == 0) cmp = a.pos.x.CompareTo(b.pos.x);
            if (cmp == 0) cmp = a.pos.y.CompareTo(b.pos.y);
            return cmp;
        }));

        int counter = 0;
        open.Add((0, counter++, start));

        HashSet<Vector2Int> visited = new();
        Dictionary<Vector2Int, Vector2Int> cameFrom = new();
        Dictionary<Vector2Int, float> cost = new() { [start] = 0 };

        while (open.Count > 0)
        {
            var current = open.Min.pos;
            open.Remove(open.Min);

            if (current == goal)
                return ReconstructPath(cameFrom, current);

            if (visited.Contains(current)) continue;
            visited.Add(current);

            foreach (var neighbor in Neighbors(current))
            {
                if (IsCollision(neighbor)) continue;

                float newCost = cost[current] + 1;
                if (!cost.ContainsKey(neighbor) || newCost < cost[neighbor])
                {
                    cameFrom[neighbor] = current;
                    cost[neighbor] = newCost;
                    open.Add((newCost, counter++, neighbor));
                }
            }
        }
        return null;
    }

    public List<Vector2Int> FusionAlgorithm()
    {
        List<Vector2Int> path = new();
        Vector2Int currentPos = startPos;
        HashSet<Vector2Int> trashSet = new(trashPositions);

        int iteration = 0;
        int maxIterations = 1000;

        while (trashSet.Count > collected.Count && iteration < maxIterations)
        {
            iteration++;
            var remainingTrash = trashSet.Except(collected).ToList();
            if (remainingTrash.Count == 0) break;

            Vector2Int target = remainingTrash[0];
            float minDist = Distance(currentPos, target);

            foreach (var t in remainingTrash)
            {
                float dist = Distance(currentPos, t);
                if (dist < minDist)
                {
                    minDist = dist;
                    target = t;
                }
            }

            var route = AStarSearch(currentPos, target) ?? DijkstraSearch(currentPos, target);
            if (route == null) break;

            for (int i = 1; i < route.Count; i++)
            {
                Vector2Int step = route[i];
                if (IsCollision(step)) break;

                path.Add(step);
                currentPos = step;

                if (trashSet.Contains(currentPos))
                    collected.Add(currentPos);
            }
        }
        return path;
    }
}
