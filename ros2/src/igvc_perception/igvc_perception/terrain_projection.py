"""Pinhole rays intersect an observed world plane; no ROS or fixed-Z fallback."""
import numpy as np


def project_plane(pixels, K, rotation, origin, plane, minimum=1., maximum=10.):
    """Return float32 world XYZ for forward intersections in the XY range band.

    Pixels are Nx2 (u,v). Rotation maps optical right/down/forward into world.
    Plane uses unit upward ``normal`` and ``normal @ point + offset == 0``.
    Invalid inputs raise ValueError; parallel, behind-camera and out-of-range
    intersections are discarded. XY range is measured from the camera origin.
    """
    try:
        pixels=np.asarray(pixels,dtype=float)
        intrinsic=np.asarray(K,dtype=float)
        rotation=np.asarray(rotation,dtype=float)
        origin=np.asarray(origin,dtype=float)
        normal=np.asarray(plane['normal'],dtype=float)
        offset=float(plane['offset'])
        minimum,maximum=float(minimum),float(maximum)
    except (KeyError,TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Malformed projection input or plane') from exc
    if pixels.ndim!=2 or pixels.shape[1]!=2 or not np.isfinite(pixels).all():
        raise ValueError('Pixels must be finite Nx2')
    if intrinsic.shape not in ((9,),(3,3)) or not np.isfinite(intrinsic).all():
        raise ValueError('K must be finite 3x3 or nine row-major values')
    intrinsic=intrinsic.reshape(3,3)
    if (intrinsic[0,0]<=0 or intrinsic[1,1]<=0 or abs(intrinsic[1,0])>1e-9
            or not np.allclose(intrinsic[2],[0,0,1],atol=1e-9,rtol=0)):
        raise ValueError('Invalid pinhole intrinsics')
    if (rotation.shape!=(3,3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-6,rtol=0)
            or not np.isclose(np.linalg.det(rotation),1.,atol=1e-6,rtol=0)):
        raise ValueError('Rotation must be finite proper orthonormal 3x3')
    if origin.shape!=(3,) or not np.isfinite(origin).all():
        raise ValueError('Origin must be finite XYZ')
    if (normal.shape!=(3,) or not np.isfinite(normal).all() or not np.isfinite(offset)
            or not np.isclose(np.linalg.norm(normal),1.,atol=1e-6,rtol=0) or normal[2]<=0):
        raise ValueError('Plane requires a finite unit upward normal and finite offset')
    if not np.isfinite([minimum,maximum]).all() or minimum<0 or maximum<minimum:
        raise ValueError('Range bounds must be finite, nonnegative and ordered')
    if len(pixels)==0:return np.empty((0,3),dtype=np.float32)
    homogeneous=np.column_stack((pixels,np.ones(len(pixels))))
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
        rays=np.linalg.solve(intrinsic,homogeneous.T).T@rotation.T
        denominator=rays@normal
        valid=np.isfinite(rays).all(axis=1)&np.isfinite(denominator)&(np.abs(denominator)>1e-9)
        scale=np.full(len(pixels),np.nan)
        scale[valid]=-(normal@origin+offset)/denominator[valid]
        points=origin+rays*scale[:,None]
        distance=np.linalg.norm(points[:,:2]-origin[:2],axis=1)
        valid&=(scale>0)&np.isfinite(points).all(axis=1)&(distance>=minimum)&(distance<=maximum)
    return points[valid].astype(np.float32)
