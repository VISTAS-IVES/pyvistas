#version 330

uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;

in vec3 fragPosition;
in vec3 fragNormal;

out vec4 finalColor;

const vec3 lightIntensity = vec3(1.0, 1.0, 1.0);
const vec3 ambientLight = vec3(.0, .0, .0);

void main() {

	//finalColor = vec4(1.0);

    mat3 normalMatrix = transpose(inverse(mat3(modelViewMatrix)));
    vec3 normal = normalize(normalMatrix * fragNormal);

    vec3 surfaceToLight = fragPosition - cameraPosition;

    float brightness = clamp(dot(normal, surfaceToLight) / (length(surfaceToLight) * length(normal)), 0, 1);
    brightness += clamp(dot(normal, -surfaceToLight) / (length(-surfaceToLight) * length(normal)), 0, 1);

    finalColor = vec4(ambientLight + brightness * lightIntensity * vec3(.5), 1.);
}
