shader_type canvas_item;

// SCREEN GRADE — the whole frame, in one pass, without touching a single
// sprite (user: "keep the base art as-is, just use godot's visual toolkit").
//
// Four cheap things that together make flat pixel art read as a photographed
// place: a contrast S-curve, a split-tone that cools the shadows and warms
// the lights, a highlight lift so lamps and windows glow a little, and a
// vignette that pulls the eye off the edges.
//
// All of it is driven from the day/night cycle, so noon and 3am are graded
// differently rather than one look stretched over both.
//
// NOTE ON PALETTE: this is a POST effect on the rendered frame, not a change
// to any sprite. The art on disk stays Apollo-pure. The anti-banding dither
// film sits on a layer ABOVE this, which is what keeps the graded ramps from
// stepping visibly on a slow fade.

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;

uniform float contrast : hint_range(0.0, 0.5) = 0.17;
uniform float lift : hint_range(0.0, 0.5) = 0.10;      // highlight bloom-ish
uniform float vignette : hint_range(0.0, 1.0) = 0.30;
uniform float night : hint_range(0.0, 1.0) = 0.0;
uniform vec3 shadow_tint : source_color = vec3(0.09, 0.13, 0.22);
uniform vec3 light_tint : source_color = vec3(1.00, 0.96, 0.86);

void fragment() {
    vec4 src = texture(screen_tex, SCREEN_UV);
    vec3 c = src.rgb;

    // luminance drives everything below, so hue is never pushed around
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));

    // S-curve: darks a touch darker, brights a touch brighter, midtones held
    float s = l + contrast * (l - 0.5) * (1.0 - abs(l - 0.5) * 2.0) * 2.0;
    c *= (l > 0.001) ? (s / l) : 1.0;

    // split tone: shadows toward cold, highlights toward warm. Stronger at
    // night, because that is when a flat grey street looks most like paper.
    float amt = 0.15 + 0.22 * night;
    vec3 cool = mix(c, c * shadow_tint * 3.0, amt * (1.0 - l));
    c = mix(cool, cool * light_tint, amt * l);

    // highlight lift: only the brightest pixels, so lamps, windows, sparks
    // and the muzzle flash carry a little glow without a blur pass
    float hi = smoothstep(0.62, 1.0, l);
    c += hi * lift * light_tint;

    // vignette off the frame centre, elliptical so it suits a wide window
    vec2 d = SCREEN_UV - vec2(0.5);
    d.x *= 1.25;
    float v = 1.0 - vignette * smoothstep(0.24, 0.78, dot(d, d) * 2.0);
    c *= v;

    COLOR = vec4(clamp(c, vec3(0.0), vec3(1.0)), src.a);
}
