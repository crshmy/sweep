using UnityEngine;
using UnityEditor;

[InitializeOnLoad]
public class SelectionSizeLogger
{
    static GameObject lastSelected;

    static SelectionSizeLogger()
    {
        Selection.selectionChanged += OnSelectionChanged;
    }

    static void OnSelectionChanged()
    {
        GameObject selected = Selection.activeGameObject;

        if (selected != null && selected != lastSelected)
        {
            lastSelected = selected;
            Renderer rend = selected.GetComponent<Renderer>();
            if (rend != null)
            {
                Vector3 size = rend.bounds.size;
                Debug.Log($" '{selected.name}' 의 실제 크기: {size.x:F2}m x {size.y:F2}m x {size.z:F2}m");
            }
            else
            {
                Debug.LogWarning($"'{selected.name}'에는 Renderer가 없어 크기를 확인할 수 없음.");
            }
        }
    }
}
