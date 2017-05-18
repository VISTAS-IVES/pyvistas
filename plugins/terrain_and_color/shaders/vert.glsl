#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;
uniform float heightFactor;

in vec3 position;
in vec3 normal;
//in vec2 boundaryTexCoord;
in float value;

out float fragBrightness;
//out vec2 fragBoundaryTexCoord;
out float fragValue;

void main() {
    vec3 scale = vec3(1., heightFactor, 1.);
	vec4 eyePosition = modelViewMatrix * vec4(position * scale, 1.0);
	gl_Position = projectionMatrix * eyePosition;
    //fragBoundaryTexCoord = boundaryTexCoord;
	fragValue = value;

    // Always use vertex lighting, for simplicity
    mat3 normalMatrix = transpose(inverse(mat3(modelViewMatrix)));
	vec3 normal = normalize(normalMatrix * (normal / scale));
	vec3 surfaceToLight = eyePosition.xyz - cameraPosition;
	fragBrightness = clamp(dot(normal, surfaceToLight) / (length(surfaceToLight) * length(normal)), 0, 1);
	fragBrightness += clamp(dot(normal, -surfaceToLight) / (length(-surfaceToLight) * length(normal)), 0, 1);
}
