shader_type canvas_item;
render_mode blend_add;

// SUN SHAFTS — light raking across the district when the sun is low.
//
// Screen-space bands rather than geometry cast from the buildings. In an
// isometric view at this scale the read you want is "the light is coming
// from over there", and bands deliver that for one full-screen pass, where
// real cast volumes would need an occluder per wall and would still be
// hidden behind the rooftops most of the time.
//
// Strength is driven entirely from the clock: nothing at night, nothing at
// noon when the sun is overhead, strongest mid-morning and late afternoon
// when it is low enough to come in sideways. Indoors it closes off.

uniform float strength : hint_range(0.0, 1.0) = 0.0;
uniform float angle = -0.62;              // radians; the sun's screen bearing
uniform float drift = 0.0;                // slow movement, seconds
uniform vec3 tint : source_color = vec3(1.0, 0.93, 0.74);

void fragment() {
    vec2 uv = SCREEN_UV - vec2(0.5);
    float c = cos(angle);
    float s = sin(angle);
    float t = uv.x * c - uv.y * s;        // distance across the beams

    // three overlapping band sets at different widths so the spacing never
    // reads as a repeating pattern
    float b = 0.0;
    b += smoothstep(0.30, 1.0, sin(t * 4.5 + drift * 0.05) * 0.5 + 0.5) * 0.55;
    b += smoothstep(0.48, 1.0, sin(t * 7.5 - drift * 0.031) * 0.5 + 0.5) * 0.28;
    b += smoothstep(0.64, 1.0, sin(t * 12.0 + drift * 0.072) * 0.5 + 0.5) * 0.17;

    // the light comes from above: strongest at the top of the frame, gone
    // by the bottom, so it never looks like a flat overlay
    float fall = smoothstep(1.05, 0.10, SCREEN_UV.y);

    // dither, for the same reason the grade needs it — these are very
    // gradual ramps and they WILL contour in 8-bit otherwise
    float n = fract(sin(dot(SCREEN_UV * vec2(1920.0, 1080.0),
        vec2(12.9898, 78.233))) * 43758.5453);

    float v = b * fall * strength;
    COLOR = vec4(tint * v + (n - 0.5) / 255.0, 1.0);
}
