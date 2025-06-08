using UnityEngine;

namespace Crest
{
    [AddComponentMenu("Crest/Underwater Renderer")]
    [ExecuteAlways]
    public class MyUnderwaterRenderer : MonoBehaviour
    {
        public OceanRenderer _ocean;
        public Camera _camera;

        public enum Mode
        {
            FullScreen,
            Portal,
        }

        public Mode _mode = Mode.FullScreen;

        [Tooltip("Optional. Assign if you want this script to drive the ocean level (for example to follow player).")]
        public Transform _followTransform;

        void OnEnable()
        {
            if (_camera == null)
            {
                _camera = Camera.main;
            }

            if (_ocean == null)
            {
                _ocean = OceanRenderer.Instance;
            }

            if (_camera != null)
            {
                _camera.depthTextureMode |= DepthTextureMode.Depth;
            }
        }

        void Update()
        {
            if (_followTransform != null && _ocean != null)
            {
                Vector3 pos = _ocean.transform.position;
                pos.y = _followTransform.position.y;
                _ocean.transform.position = pos;
            }
        }
    }
}
