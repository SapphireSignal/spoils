shader_type canvas_item;

// Light moving across the menu wordmark.
//
// This replaces a narrow Control with clip_contents that swept a flat silver
// copy of the title across it. That was a HARD-EDGED VERTICAL RECTANGLE: a
// 34 px bar sliding over the letters with a visible straight edge on each
// side. Metal does not gleam in vertical bars, and the user's verdict on the
// whole title was "its just white, and it goes up and down a bit thats all,
// it seems boring" — the sweep was the only thing happening and it read as a
// rectangle, not as light.
//
// Two layers on one diagonal coordinate:
//   ambient - a wide, dim band that never stops drifting, so the wordmark is
//             alive even between sweeps. This is the half the old effect had
//             nothing of; for 5.1 of every 6 seconds it did nothing at all.
//   sweep   - a narrow bright band, once every sweep_period.
//
// Both are ADDED to RGB and scaled by the sprite's own alpha, exactly as
// flash.gdshader does it, so the silhouette can never fatten and the
// transparent margin around the letters stays transparent.
//
// THE INTENSITY IS QUANTISED TO WHOLE STEPS ON PURPOSE. A smooth ramp across
// a pixel-art sprite reads as a gradient nothing else in the game has, and
// the standing rule is that any gradual ramp has to dither itself or it
// bands. Stepping it sidesteps both: it matches the banded cel light the menu
// paintings already use, and a stepped value cannot band.

uniform float sweep_period = 6.0;   // seconds between bright sweeps
uniform float sweep_time = 0.9;     // how long one sweep takes to cross
uniform float slope = 0.55;         // how far the band leans off vertical
uniform float band = 0.16;          // band half-width, in diagonal units
uniform float ambient_gain = 0.25;
uniform float sweep_gain = 0.85;
uniform float steps = 5.0;
uniform vec3 gleam_color = vec3(1.0, 1.0, 0.96);

void fragment() {
    float a = COLOR.a;
    float span = 1.0 + slope;
    float d = UV.x + UV.y * slope;

    // ambient: wide, dim, drifting back and forth forever
    float ap = (0.5 + 0.5 * sin(TIME * 0.35)) * span;
    float amb = smoothstep(band * 2.5, 0.0, abs(d - ap)) * ambient_gain;

    // sweep: narrow and bright, and it starts fully off the leading edge so
    // it enters and leaves rather than popping on over the letters
    float ph = mod(TIME, sweep_period);
    float sw = 0.0;
    if (ph < sweep_time) {
        float sp = (ph / sweep_time) * (span + band * 2.0) - band;
        sw = smoothstep(band, 0.0, abs(d - sp)) * sweep_gain;
    }

    float g = floor((amb + sw) * steps) / steps;
    COLOR.rgb = clamp(COLOR.rgb + gleam_color * g * a, 0.0, 1.0);
}
