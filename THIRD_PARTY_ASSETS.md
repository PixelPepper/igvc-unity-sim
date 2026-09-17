# Asset provenance and public distribution

The project owner requested public GitHub distribution on 2026-09-16. This
supersedes the earlier private-repository workflow; it does not establish or
grant third-party intellectual-property rights.

- R3-a robot meshes and derived URDF came from the owner's supplied SolidWorks
  export. Original CAD files remain external. Provenance hashes are retained in
  the description package. Separate redistribution permissions for embedded
  vendor geometry have not been verified.
- The supplied RPLIDAR CAD and derived geometry have recorded provenance but no
  verified redistribution license in this repository.
- Camera geometry references Luxonis hardware resources. Availability of vendor
  CAD is not itself a blanket license for all derived assets.
- SoonerRobotics environment assets are downloaded during local preparation.
  They are excluded from Git and the ROS container; their reuse terms remain
  unresolved.
- Unity Editor/player dependencies are not included in the ROS image. Users
  install Unity and activate their own applicable license.
- ROS, Nav2, Ubuntu and other image dependencies retain their upstream licenses
  and installed notices. ROS-TCP-Endpoint is pinned in the Dockerfile.

There is no new blanket open-source license for the project or its CAD assets.
Public source availability and permission to redistribute are distinct.
