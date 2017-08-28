#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;
uniform float heightFactor;
uniform bool perVertexColor;
uniform bool perVertexLighting;
uniform bool hasColor;
uniform bool isFiltered;
uniform float filterMin;
uniform float filterMax;
uniform float noDataValue;
uniform float minValue;
uniform float maxValue;
uniform vec4 minColor;
uniform vec4 maxColor;
uniform vec4 noDataColor;

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 uv;
layout(location = 3) in float value;

out vec3 fragPosition;
out vec3 fragNormal;
out vec4 fragColor;
out float fragBrightness;
out vec2 fragBoundaryTexCoord;
out float fragValue;

void hsvToRGB(in vec4 colorIn, out vec4 colorOut) {
    float r, g, b;
    float h = colorIn.x;
    float s = colorIn.y;
    float v = colorIn.z;

    int hi = (int(h)/60) % 60;
    float f = (h/60.0) - (int(h)/60);
    float p = v * (1-s);
    float q = v * (1 - f*s);
    float t = v * (1 - (1-f)*s);

    switch (hi) {
    case 0:
        r = v;
        g = t;
        b = p;
        break;
    case 1:
        r = q;
        g = v;
        b = p;
        break;
    case 2:
        r = p;
        g = v;
        b = t;
        break;
    case 3:
        r = p;
        g = q;
        b = v;
        break;
    case 4:
        r = t;
        g = p;
        b = v;
        break;
    case 5:
        r = v;
        g = p;
        b = q;
        break;
    default:
        r = 0.;
        g = 0.;
        b = 0.;
    }

    colorOut = vec4(r, g, b, colorIn.w);
}

void interpolateColor(out vec4 colorOut) {
	if (round(value) == round(noDataValue) || (isFiltered && (value < filterMin || value > filterMax))) {
		hsvToRGB(noDataColor, colorOut);
		return;
	}
    if (value < minValue) {
        hsvToRGB(minColor, colorOut);
        return;
    }
    if (value > maxValue) {
        hsvToRGB(maxColor, colorOut);
        return;
    }

    float factor = (value - minValue) / (maxValue - minValue);
    vec4 color = abs(minColor + (maxColor - minColor) * factor);
    color.x = round(color.x);
    hsvToRGB(color, colorOut);
}

void main() {
    vec3 scale = vec3(1., 1., heightFactor);
	vec4 eyePosition = modelViewMatrix * vec4(position * scale, 1.0);
	//vec4 eyePosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * eyePosition;
    fragPosition = eyePosition.xyz;
    fragNormal = normal / scale;
    fragBoundaryTexCoord = uv;
	fragValue = value;

	if (perVertexColor) {
		interpolateColor(fragColor);
	}
	if (perVertexLighting) {
		mat3 normalMatrix = transpose(inverse(mat3(modelViewMatrix)));
		vec3 normal = normalize(normalMatrix * fragNormal);

		vec3 surfaceToLight = fragPosition - cameraPosition;

		fragBrightness = clamp(dot(normal, surfaceToLight) / (length(surfaceToLight) * length(normal)), 0, 1);
		fragBrightness += clamp(dot(normal, -surfaceToLight) / (length(-surfaceToLight) * length(normal)), 0, 1);
	}
}
