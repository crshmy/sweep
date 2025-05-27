using System;
using System.Collections.Generic;
using UnityEngine;

public class SweepAlgorithm : MonoBehaviour
{
    public int gridSize = 50;
    public Vector2Int startPos;

    public List<Vector2Int> trashPositions;
    public List<Vector2Int> obstaclePositions;

    private HashSet<Vector2Int> collected = new HashSet<Vector2Int>();

    // 유클리디안 거리 계산
    private float Distance(Vector2Int a, Vector2Int b)
    {
        return Vector2Int.Distance(a, b);
    }

    // 장애물 체크
    private bool IsCollision(Vector2Int pos)
    {
        return obstaclePositions.Contains(pos);
    }

    // 인접 4방향 좌표 반환
    private List<Vector2Int> Neighbors(Vector2Int pos)
    {
        List<Vector2Int> result = new List<Vector2Int>();

        Vector2Int[] directions = new Vector2Int[]
        {
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

    // A* 알고리즘 구현
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

        Dictionary<Vector2Int, Vector2Int> cameFrom = new Dictionary<Vector2Int, Vector2Int>();
        Dictionary<Vector2Int, float> gScore = new Dictionary<Vector2Int, float>();
        gScore[start] = 0;

        while (openSet.Count > 0)
        {
            var currentTuple = openSet.Min;
            openSet.Remove(currentTuple);
            Vector2Int current = currentTuple.pos;

            if (current == goal)
            {
                return ReconstructPath(cameFrom, current);
            }

            foreach (var neighbor in Neighbors(current))
            {
                if (IsCollision(neighbor)) continue;

                float tentative_gScore = gScore[current] + 1;
                if (!gScore.ContainsKey(neighbor) || tentative_gScore < gScore[neighbor])
                {
                    cameFrom[neighbor] = current;
                    gScore[neighbor] = tentative_gScore;
                    float fScore = tentative_gScore + Distance(neighbor, goal);
                    openSet.Add((fScore, counter++, neighbor));
                }
            }
        }

        return null; // 경로 없음
    }

    // Dijkstra 알고리즘 구현
    private List<Vector2Int> DijkstraSearch(Vector2Int start, Vector2Int goal)
    {
        var heap = new SortedSet<(float cost, int count, Vector2Int pos)>(Comparer<(float, int, Vector2Int)>.Create((a, b) =>
        {
            int cmp = a.cost.CompareTo(b.cost);
            if (cmp == 0) cmp = a.count.CompareTo(b.count);
            if (cmp == 0) cmp = a.pos.x.CompareTo(b.pos.x);
            if (cmp == 0) cmp = a.pos.y.CompareTo(b.pos.y);
            return cmp;
        }));

        int counter = 0;
        heap.Add((0, counter++, start));

        HashSet<Vector2Int> visited = new HashSet<Vector2Int>();
        Dictionary<Vector2Int, Vector2Int> cameFrom = new Dictionary<Vector2Int, Vector2Int>();
        Dictionary<Vector2Int, float> cost = new Dictionary<Vector2Int, float>();
        cost[start] = 0;

        while (heap.Count > 0)
        {
            var currentTuple = heap.Min;
            heap.Remove(currentTuple);
            Vector2Int current = currentTuple.pos;

            if (current == goal)
            {
                return ReconstructPath(cameFrom, current);
            }

            if (visited.Contains(current)) continue;
            visited.Add(current);

            foreach (var neighbor in Neighbors(current))
            {
                if (IsCollision(neighbor)) continue;
                float newCost = cost[current] + 1;
                if (!cost.ContainsKey(neighbor) || newCost < cost[neighbor])
                {
                    cost[neighbor] = newCost;
                    cameFrom[neighbor] = current;
                    heap.Add((newCost, counter++, neighbor));
                }
            }
        }

        return null;
    }

    // 경로 역추적
    private List<Vector2Int> ReconstructPath(Dictionary<Vector2Int, Vector2Int> cameFrom, Vector2Int current)
    {
        List<Vector2Int> path = new List<Vector2Int> { current };
        while (cameFrom.ContainsKey(current))
        {
            current = cameFrom[current];
            path.Add(current);
        }
        path.Reverse();
        return path;
    }

    // Fusion 알고리즘 (메인 루프)
    public List<Vector2Int> FusionAlgorithm()
    {
        List<Vector2Int> path = new List<Vector2Int>();
        Vector2Int currentPos = startPos;
        HashSet<Vector2Int> trashSet = new HashSet<Vector2Int>(trashPositions);
        int maxIterations = 1000;
        int iteration = 0;

        while (trashSet.Count > collected.Count && iteration < maxIterations)
        {
            iteration++;
            var remainingTrash = new List<Vector2Int>();
            foreach (var t in trashSet)
            {
                if (!collected.Contains(t))
                    remainingTrash.Add(t);
            }
            if (remainingTrash.Count == 0) break;

            // 1) 가장 가까운 쓰레기 찾기
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

            // 2) A* 경로 찾기
            var route = AStarSearch(currentPos, target);

            // A* 실패하면 Dijkstra로
            if (route == null)
                route = DijkstraSearch(currentPos, target);

            // 둘 다 실패하면 다른 타겟 찾기
            if (route == null)
            {
                bool found = false;
                var altTargets = new List<Vector2Int>(remainingTrash);
                altTargets.Remove(target);
                altTargets.Sort((a, b) => Distance(currentPos, a).CompareTo(Distance(currentPos, b)));

                foreach (var alt in altTargets)
                {
                    route = AStarSearch(currentPos, alt);
                    if (route == null)
                        route = DijkstraSearch(currentPos, alt);
                    if (route != null)
                    {
                        target = alt;
                        found = true;
                        break;
                    }
                }
                if (!found) break; // 갈 수 있는 곳 없음
            }

            // 3) 경로 이동, 수거
            for (int i = 1; i < route.Count; i++)
            {
                Vector2Int step = route[i];

                // 장애물 바로 앞이면 우회 시도
                if (IsCollision(step))
                {
                    bool moved = false;
                    foreach (var neighbor in Neighbors(currentPos))
                    {
                        if (!IsCollision(neighbor))
                        {
                            step = neighbor;
                            moved = true;
                            break;
                        }
                    }
                    if (!moved) break; // 이동 불가
                }

                path.Add(step);
                currentPos = step;

                if (trashSet.Contains(currentPos) && !collected.Contains(currentPos))
                {
                    collected.Add(currentPos);
                    // Debug.Log($"Collected trash at {currentPos}");
                }
            }
        }

        return path;
    }
}