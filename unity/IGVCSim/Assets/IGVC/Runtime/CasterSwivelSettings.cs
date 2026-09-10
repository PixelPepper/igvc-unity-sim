using System;

namespace IGVC
{
    [Serializable]
    public sealed class CasterSwivelSettings
    {
        public double alignment_distance_m, maximum_rate_rad_s, stationary_speed_m_s;
        public CasterSwivel Create() => new CasterSwivel(alignment_distance_m, maximum_rate_rad_s, stationary_speed_m_s);
    }
}
