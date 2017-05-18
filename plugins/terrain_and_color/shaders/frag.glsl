#version 330

uniform bool hasColor;
uniform bool isFiltered;
uniform float filterMin;
uniform float filterMax;
//uniform bool hasBoundaries;
uniform bool hideNoData;
uniform float noDataValue;
uniform float minValue;
uniform float maxValue;
uniform vec4 minColor;
uniform vec4 maxColor;
uniform vec4 noDataColor;
uniform vec4 boundaryColor;
uniform sampler2D boundaryTexture;

in float fragBrightness;
//in vec2 fragBoundaryTexCoord;
in float fragValue;

out vec4 finalColor;

const vec4 lightColor = vec4(1.0, 1.0, 1.0, 1.0);
const vec3 lightIntensity = vec3(1.0, 1.0, 1.0);
const vec3 ambientLight = vec3(.0, .0, .0);

void hsvToRGB(in vec4 colorIn, out vec4 colorOut) {
    float r, g, b;
    float h = colorIn.x;
    float s = colorIn.y;
    float v = colorIn.z;

    int hi = (int(h) / 60) % 60;
    float f = (h / 60.0) - (int(h) / 60);
    float p = v * (1 - s);
    float q = v * (1 - f*s);
    float t = v * (1 - (1 - f)*s);

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

bool fragValueIsFiltered() {
    return isFiltered && (fragValue < filterMin || fragValue > filterMax);
}

void interpolateColor(out vec4 colorOut) {
    if (round(fragValue) == round(noDataValue) || fragValueIsFiltered()) {
        hsvToRGB(noDataColor, colorOut);
        return;
    }
    if (fragValue < minValue) {
        hsvToRGB(minColor, colorOut);
        return;
    }
    if (fragValue > maxValue) {
        hsvToRGB(maxColor, colorOut);
        return;
    }

    float factor = (fragValue - minValue) / (maxValue - minValue);
    vec4 color = abs(minColor + (maxColor - minColor) * factor);
    color.x = round(color.x);
    hsvToRGB(color, colorOut);
}

void main() {
    if (hideNoData && round(fragValue) == round(noDataValue)) {
        discard;
    }

    vec4 baseColor = lightColor;
    if (hasColor) {
        interpolateColor(baseColor);
    }
    else {
        hsvToRGB(noDataColor, baseColor);
    }

    //if (hasBoundaries) {
    //    vec4 fragBoundaryColor = texture(boundaryTexture, fragBoundaryTexCoord);
    //    if (fragBoundaryColor.r < 1) {
    //        hsvToRGB(boundaryColor, baseColor);
    //    }
    //}

    finalColor = vec4(ambientLight + fragBrightness * lightIntensity * baseColor.xyz, 1.);
}
