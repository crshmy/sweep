using System.Collections.Generic;
using UnityEngine;
using System.IO;

public class LogManager : MonoBehaviour
{
    private List<string> logEntries = new List<string>();

    public void Log(string message, Vector3 position)
    {
        string entry = $"{Time.time:F2},{message},({position.x:F2},{position.y:F2},{position.z:F2})";
        logEntries.Add(entry);
        Debug.Log(entry);
    }

    public void SaveToCSV(string algorithmName)
    {
        string folderPath = Application.dataPath + "/Logs";
        if (!Directory.Exists(folderPath))
            Directory.CreateDirectory(folderPath);

        string timestamp = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
        string filename = $"Log_{algorithmName}_{timestamp}.csv";
        string path = Path.Combine(folderPath, filename);

        File.WriteAllLines(path, logEntries);
        Debug.Log("·Î±× ÀúÀåµÊ: " + path);
    }
}
