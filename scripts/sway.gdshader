shader_type canvas_item;

// FOLIAGE SWAY — a WHOLE-PIXEL horizontal shift, never a rotation and never a
// scale. Both of those resample pixel art and are banned project-wide.
//
// It works in the FRAGMENT stage on purpose. A vertex-stage shear would move
// the quad's corners and the texture would be sampled off-axis, which ragged
// every column. Shifting the UV by an INTEGER number of TEXELS instead moves
// whole rows of pixels sideways, so the art lands exactly on its own grid and
// nothing is ever resampled.
//
// THE BASE IS PINNED AND THE CROWN MOVES: the shift is weighted by height, so
// a trunk stays put while the canopy leans. Without that the whole tree slides
// sideways and reads as a rendering fault rather than as wind.
//
// The PHASE COMES FROM THE INSTANCE'S OWN WORLD POSITION, hashed in the vertex
// stage and handed down as a varying. That means every tree sways on its own
// clock from ONE SHARED MATERIAL — no per-instance material, no per-tree rng
// draw. The second part matters more than it looks: the district layout is
// FIXED, and taking an extra draw from the builder's rng would re-roll the
// whole map.

uniform float amplitude = 2.0;   // whole pixels of throw at the very top
uniform float speed = 0.9;
uniform float base_hold = 0.45;  // fraction from the BOTTOM that never moves

varying float v_phase;

void vertex() {
	// MODEL_MATRIX[2].xy is this instance's world translation
	vec2 wp = MODEL_MATRIX[2].xy;
	v_phase = fract(sin(dot(wp, vec2(12.9898, 78.233))) * 43758.5453) * 6.2831853;
}

void fragment() {
	// UV.y is 0 at the TOP of the sprite and 1 at the bottom, so the canopy is
	// the small end and the trunk the large one.
	float w = clamp((1.0 - UV.y - base_hold) / max(0.0001, 1.0 - base_hold),
		0.0, 1.0);
	float texels = float(textureSize(TEXTURE, 0).x);
	// ROUNDED TO A WHOLE TEXEL. This is the line that keeps it on the grid.
	float amt = floor(sin(TIME * speed + v_phase) * amplitude * w + 0.5);
	vec2 uv = UV + vec2(amt / texels, 0.0);
	// a row shifted past its own edge must vanish, not smear: sampling outside
	// clamps to the edge texel and would drag a column of leaf colour off the
	// side of the sprite
	if (uv.x < 0.0 || uv.x > 1.0) {
		COLOR = vec4(0.0);
	} else {
		COLOR = texture(TEXTURE, uv);
	}
}
