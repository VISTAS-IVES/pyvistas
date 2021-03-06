#version 330

uniform mat4 modelViewMatrix;

in vec3 fragPosition;
in vec3 fragNormal;

out vec4 finalColor;

const vec3 lightIntensity = vec3(1.0, 1.0, 1.0);
const vec3 ambientLight = vec3(.0, .0, .0);
const vec3 lightPosition = vec3(0., 1.0, 0.0);
const vec3 grey = vec3(0.5);

void main() {

    mat3 normalMatrix = transpose(inverse(mat3(modelViewMatrix)));
    vec3 normal = normalize(normalMatrix * fragNormal);

    vec3 surfaceToLight = fragPosition - lightPosition;

    float brightness = clamp(dot(normal, surfaceToLight) / (length(surfaceToLight) * length(normal)), 0, 1);
    brightness += clamp(dot(normal, -surfaceToLight) / (length(-surfaceToLight) * length(normal)), 0, 1);

    finalColor = vec4(ambientLight + brightness * lightIntensity * grey, 1);
}
