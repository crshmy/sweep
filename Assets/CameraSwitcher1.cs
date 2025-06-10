using UnityEngine;
using Cinemachine;

public class CameraSwitcher : MonoBehaviour
{
    public CinemachineVirtualCamera followCam;
    public CinemachineVirtualCamera topCam;
    public CinemachineVirtualCamera frontCam;

    private CinemachineVirtualCamera[] allCams;
    private int currentIndex = 0;

    void Start()
    {
        allCams = new CinemachineVirtualCamera[] { followCam, topCam, frontCam };
        SetActiveCamera(0);
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.C))
        {
            currentIndex = (currentIndex + 1) % allCams.Length;
            SetActiveCamera(currentIndex);
        }
    }

    void SetActiveCamera(int index)
    {
        for (int i = 0; i < allCams.Length; i++)
        {
            allCams[i].Priority = (i == index) ? 10 : 0;
        }
    }
}
