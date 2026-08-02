shader_type canvas_item;

// A hit flash that does NOT touch the base art: it blends the sprite's own
// pixels toward one flat colour and leaves alpha alone, so the silhouette,
// the pixel grid and the palette of the underlying sprite are all untouched
// when flash is 0 — which it is for all but a fifth of a second.
//
// Deliberately not a whole-screen effect: a per-sprite flash tells you WHAT
// got hit, which a full-screen tint never can.

uniform float flash : hint_range(0.0, 1.0) = 0.0;
uniform vec4 flash_color : source_color = vec4(0.922, 0.929, 0.914, 1.0);

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    // mix on RGB only, and scale by the sprite's own alpha so the flash can
    // never bleed into transparent pixels and fatten the silhouette
    vec3 lit = mix(tex.rgb, flash_color.rgb, flash * tex.a);
    COLOR = vec4(lit, tex.a) * COLOR;
}
