#version 330

uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;
uniform float alpha;

in vec3 fragColor;
in vec3 fragPosition;
in vec3 fragNormal;
in float fragBrightness;

out vec4 finalColor;

const vec4 lightColor = vec4(1.0, 1.0, 1.0, 1.0);
const vec3 lightIntensity = vec3(1.0, 1.0, 1.0);
const vec3 ambientLight = vec3(.0, .0, .0);
const vec3 lightPosition = vec3(0., 1.0, 0.0);

const int perVertexLighting = 0;

void main() {
    vec3 normal = normalize(transpose(inverse(mat3(modelViewMatrix))) * fragNormal);
    vec3 surfaceToLight = fragPosition - cameraPosition;
    float brightness = clamp(dot(normal, surfaceToLight) / (length(surfaceToLight) * length(normal)), 0, 1);
    brightness += clamp(dot(normal, -surfaceToLight) / (length(-surfaceToLight) * length(normal)), 0, 1);    	
	finalColor = vec4(ambientLight + brightness * lightIntensity * fragColor.xyz, alpha);
}
