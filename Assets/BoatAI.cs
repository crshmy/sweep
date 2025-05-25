using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class BoatAI : MonoBehaviour
{
    public float speed = 5f;
    private GameObject target;
    private Rigidbody rb;

    void Start()
    {
        rb = GetComponent<Rigidbody>();
    }

    void FixedUpdate()
    {
        if (target == null)
        {
            GameObject[] trashList = GameObject.FindGameObjectsWithTag("Trash");
            float minDist = Mathf.Infinity;
            GameObject closest = null;

            foreach (var t in trashList)
            {
                float dist = Vector3.Distance(transform.position, t.transform.position);
                if (dist < minDist)
                {
                    minDist = dist;
                    closest = t;
                }
            }

            if (closest != null)
            {
                target = closest;
            }
            else
            {
                var eval = FindObjectOfType<EvaluationManager>();
                if (eval != null && !eval.hasSaved)
                {
                    eval.SaveResults();
                    Debug.Log(" 모든 쓰레기 수거 완료. 저장하고 보트 종료.");
                }

                enabled = false;
                return;
            }
        }

        if (target != null)
        {
            Vector3 dir = (target.transform.position - transform.position).normalized;
            rb.MovePosition(rb.position + dir * speed * Time.fixedDeltaTime);

            Quaternion targetRot = Quaternion.LookRotation(dir);
            rb.MoveRotation(Quaternion.Slerp(rb.rotation, targetRot, 5f * Time.fixedDeltaTime));
        }
    }

    private void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Trash"))
        {
            var eval = FindObjectOfType<EvaluationManager>();
            if (eval != null)
            {
                eval.TrashCollected(other.gameObject);
            }

            Destroy(other.gameObject);
            target = null;
        }
    }

}
