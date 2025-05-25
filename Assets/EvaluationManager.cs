using System.Collections.Generic;
using UnityEngine;
using System.IO;

public class EvaluationManager : MonoBehaviour
{
    public Transform boat;
    public string algorithmName = "Greedy"; // 여기를 유니티에서 바꿔서 실험

    public List<GameObject> allTrash = new List<GameObject>();

    private Vector3 lastBoatPosition;
    private float totalDistance = 0f;
    private float timer = 0f;
    private int collected = 0;
    public bool hasSaved = false;

    void Start()
    {
        lastBoatPosition = boat.position;
    }

    void Update()
    {
        totalDistance += Vector3.Distance(boat.position, lastBoatPosition);
        lastBoatPosition = boat.position;
        timer += Time.deltaTime;
    }

    public void RegisterTrash(GameObject obj)
    {
        allTrash.Add(obj);
    }

    public void TrashCollected()
    {
        collected++;
    }

    public void TrashCollected(GameObject trash)
    {
        if (allTrash.Contains(trash))
        {
            allTrash.Remove(trash); // 이미 수거한 거면 다시 세지 않게
            collected++;
        }
    }

    public void SaveResults()
    {
        if (hasSaved) return;
        hasSaved = true;

        int total = collected + allTrash.Count;
        float collectionRate = total > 0 ? (float)collected / total : 0f;

        string path = Application.dataPath + $"/result_{algorithmName}.csv";
        string result =
            $"Algorithm,{algorithmName}\n" +
            $"CollectionRate,{collectionRate:F4}\n" +
            $"SearchDistance,{totalDistance:F2}\n" +
            $"ElapsedTime,{timer:F4}\n";

        File.WriteAllText(path, result);
        Debug.Log(" 결과 저장됨: " + path);
    }

}
