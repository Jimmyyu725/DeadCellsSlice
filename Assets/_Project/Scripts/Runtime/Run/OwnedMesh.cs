using System.Collections.Generic;
using DeadCells.Core;
using DeadCells.Enemies;
using DeadCells.Environment;
using DeadCells.Items;
using DeadCells.Meta;
using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.Run
{
    /// <summary>Destroys a runtime-combined mesh with its object.</summary>
    public class OwnedMesh : MonoBehaviour
    {
        void OnDestroy()
        {
            var mf = GetComponent<MeshFilter>();
            if (mf != null && mf.sharedMesh != null)
                Destroy(mf.sharedMesh);
        }
    }
}
