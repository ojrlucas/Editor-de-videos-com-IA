// Shaders GLSL (WebGL2). Tudo é procedural: nenhuma textura/foto é usada.
export const VERT = `#version 300 es
in vec2 aPos;
void main(){ gl_Position = vec4(aPos, 0., 1.); }`;

const COMMON = `#version 300 es
precision highp float;
uniform vec2 uRes;
uniform float uT;
out vec4 outColor;

float hash11(float p){ p = fract(p*.1031); p *= p+33.33; p *= p+p; return fract(p); }
float hash21(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*.1031); p3 += dot(p3, p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
float hash31(vec3 p3){ p3 = fract(p3*.1031); p3 += dot(p3, p3.zyx+31.32); return fract((p3.x+p3.y)*p3.z); }
vec2 hash22(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*vec3(.1031,.1030,.0973)); p3 += dot(p3, p3.yzx+33.33); return fract((p3.xx+p3.yz)*p3.zy); }

float vnoise2(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f*f*f*(f*(f*6.-15.)+10.);
  return mix(mix(hash21(i), hash21(i+vec2(1,0)), u.x),
             mix(hash21(i+vec2(0,1)), hash21(i+vec2(1,1)), u.x), u.y);
}
float vnoise3(vec3 p){
  vec3 i = floor(p), f = fract(p);
  vec3 u = f*f*f*(f*(f*6.-15.)+10.);
  return mix(mix(mix(hash31(i), hash31(i+vec3(1,0,0)), u.x),
                 mix(hash31(i+vec3(0,1,0)), hash31(i+vec3(1,1,0)), u.x), u.y),
             mix(mix(hash31(i+vec3(0,0,1)), hash31(i+vec3(1,0,1)), u.x),
                 mix(hash31(i+vec3(0,1,1)), hash31(i+vec3(1,1,1)), u.x), u.y), u.z);
}
float fbm2(vec2 p, int oct){
  float a = .5, s = 0.;
  mat2 m = mat2(1.6,1.2,-1.2,1.6);
  for(int i=0;i<8;i++){ if(i>=oct) break; s += a*vnoise2(p); p = m*p; a *= .5; }
  return s;
}
float fbm3(vec3 p, int oct){
  float a = .5, s = 0.;
  for(int i=0;i<8;i++){ if(i>=oct) break; s += a*vnoise3(p); p = p*2.03 + vec3(1.7,9.2,3.1); a *= .5; }
  return s;
}
mat2 rot2(float a){ float c = cos(a), s = sin(a); return mat2(c,-s,s,c); }
vec3 tonemap(vec3 c){ c = 1. - exp(-c*1.35); return pow(c, vec3(.92)); }
`;

// ---------------------------------------------------------------------------
// PLANETA: espaço profundo + esfera com atmosfera turbulenta (HD 189733 b)
// ---------------------------------------------------------------------------
export const PLANET_FRAG = COMMON + `
uniform float uR;        // raio do planeta (em unidades de meia-largura)
uniform vec2  uC;        // centro do planeta
uniform float uRot;      // rotação / escoamento
uniform float uGrid;     // grade científica (0..1)
uniform float uStarZoom; // viagem através das estrelas
uniform float uFlash;
uniform float uDetail;   // octaves extras quando perto

vec3 stars(vec2 p){
  vec3 col = vec3(0.);
  for(int l=0;l<4;l++){
    float fl = float(l);
    float sc = (9. + fl*14.) ;
    float z = exp(uStarZoom*(.25+fl*.18));
    vec2 q = p/z*sc + fl*13.7;
    vec2 id = floor(q), f = fract(q)-.5;
    float h = hash21(id+fl*7.1);
    if(h > .86 - fl*.02){
      vec2 o = (hash22(id)-.5)*.6;
      float d = length(f-o);
      float size = (.025 + .05*hash21(id+3.3))*(1. + .6*fl);
      float tw = .75 + .25*sin(uT*(2.+h*6.)+h*40.);
      float s = smoothstep(size, 0., d) * tw;
      vec3 tint = mix(vec3(.7,.8,1.), vec3(1.,.85,.7), hash21(id+9.9));
      col += s*tint*(.5+hash21(id+1.3));
    }
  }
  return col;
}

void main(){
  vec2 frag = gl_FragCoord.xy;
  vec2 p = (frag - .5*uRes)/(.5*uRes.x);
  vec3 col = vec3(0.);

  // fundo: gradiente profundo + nebulosa sutil
  float neb = fbm2(p*.9 + vec2(3.,uT*.01), 5);
  col += vec3(.004,.010,.03) + vec3(.01,.025,.07)*smoothstep(.35,.8,neb);
  col += stars(p)*1.1;

  // estrela hospedeira distante (luz de contra-luz alaranjada)
  vec2 sunP = vec2(.95, 1.55);
  float ds = length(p - sunP);
  col += vec3(1.,.62,.32)*(.035/(ds*ds+.02))*(.5+.5*smoothstep(0.,1.,uStarZoom*.2+.6));

  vec2 q = (p - uC)/uR;
  float r2 = dot(q,q);
  float r = sqrt(r2);
  vec3 L = normalize(vec3(.88,.36,.30));

  // halo atmosférico externo
  float outer = exp(-max(r-1.,0.)*(11./max(.6,min(uR,1.4)))) * step(1.,r);
  float facing = pow(max(dot(normalize(q+1e-5), L.xy/length(L.xy)),0.)*.6+.4, 2.);
  col += vec3(.12,.42,1.)*outer*.55*facing;
  col += vec3(.35,.7,1.)*exp(-max(r-1.,0.)*45.)*step(1.,r)*.9*facing;

  if(r2 < 1.){
    float z = sqrt(1.-r2);
    vec3 n = vec3(q, z);
    // coordenadas no referencial do planeta
    float lat = n.y;
    float ang = uRot*(.05 + .05*cos(lat*3.2)) ;
    float cs = cos(ang), sn = sin(ang);
    vec3 m = vec3(cs*n.x + sn*n.z, n.y, -sn*n.x + cs*n.z);
    float lon = atan(m.x, m.z);
    vec3 cyl = vec3(cos(lon)*1.3, sin(lon)*1.3, lat*3.6);

    // grande tempestade (vórtice)
    vec3 sc = normalize(vec3(.35,-.28,.9));
    float dd = length(m - sc);
    float tw = 4.5*exp(-dd*dd*7.);
    vec3 k = sc; vec3 v = m - sc*dot(m,sc);
    vec3 vr = v*cos(tw) + cross(k,v)*sin(tw);
    vec3 mm = sc*dot(m,sc) + vr;
    vec3 cyl2 = vec3(cos(atan(mm.x,mm.z))*1.3, sin(atan(mm.x,mm.z))*1.3, mm.y*3.6);

    float warp = fbm3(cyl2*1.7 + vec3(0.,0.,uRot*.03), 4);
    float bands = .5 + .5*sin(mm.y*10. + 3.2*warp + 1.5*fbm3(cyl2*.8, 3));
    float det = fbm3(cyl2*vec3(2.4,2.4,4.5) + warp*1.8 + vec3(uRot*.02,0.,0.), 5 + int(uDetail));
    float fine = fbm3(cyl2*vec3(7.,7.,14.) + warp*2.5, 4 + int(uDetail));

    vec3 deep  = vec3(.005,.035,.20);
    vec3 midc  = vec3(.03,.19,.80);
    vec3 light = vec3(.22,.58,1.0);
    vec3 pale  = vec3(.70,.90,1.0);
    vec3 albedo = mix(deep, midc, smoothstep(.15,.85,bands));
    albedo = mix(albedo, light, smoothstep(.45,.85,det)*.75);
    albedo = mix(albedo, pale, smoothstep(.62,.95,det*.6+fine*.5)*.55);
    albedo = mix(albedo, deep*.25, smoothstep(.52,.7,fine)*.45*(1.-smoothstep(.8,1.,bands)));
    // olho da tempestade
    albedo = mix(albedo, vec3(.0,.03,.14), smoothstep(.16,.02,dd)*.8);

    float diff = dot(n, L);
    float lit = smoothstep(-.28,.55,diff);
    float wrap = smoothstep(-.5,.2,diff);
    vec3 amb = vec3(.006,.022,.08);
    vec3 c = albedo*(amb + lit*1.55 + .0*wrap);

    // dispersão no terminador (tom quente discreto)
    c += vec3(1.,.55,.28)*exp(-pow((diff+.02)*5.5,2.))*.10*(1.-lit*.4);
    // brilho especular da névoa de alta altitude
    vec3 H = normalize(L + vec3(0.,0.,1.));
    c += vec3(.5,.75,1.)*pow(max(dot(n,H),0.),22.)*.30*smoothstep(.4,.9,det);
    // limbo: espalhamento atmosférico (Fresnel)
    float fres = pow(1.-z, 2.6);
    c += vec3(.15,.55,1.)*fres*(.25+1.5*smoothstep(-.4,.7,diff));
    c += vec3(.5,.85,1.)*pow(1.-z, 7.)*1.3*smoothstep(-.2,.6,diff);

    // grade científica
    float glat = abs(fract(asin(clamp(m.y,-1.,1.))/3.14159*12.)-.5);
    float glon = abs(fract(lon/6.28318*24.)-.5);
    float gl = smoothstep(.03,.0,glat) + smoothstep(.03,.0,glon);
    c += vec3(.25,.75,1.)*gl*uGrid*.32*(.4+.6*z);

    // borda suave
    float edge = smoothstep(1.,.992,r);
    col = mix(col, c, edge);
  }
  col += vec3(.4,.75,1.)*uFlash;
  col = tonemap(col);
  col += (hash21(frag+uT)-.5)/255.;
  outColor = vec4(col,1.);
}`;

// ---------------------------------------------------------------------------
// ATMOSFERA: voo através de camadas de nuvens volumétricas (paralaxe) + vórtice
// ---------------------------------------------------------------------------
export const CLOUD_FRAG = COMMON + `
uniform float uStretch;  // esticamento das nuvens ao longo do vento
uniform float uFlash;    // relâmpago
uniform vec2  uShake;
uniform float uSwirl;    // intensidade do vórtice
uniform vec2  uSwirlC;
uniform float uDark;
uniform float uBase;     // fase de avanço (integral da velocidade)
uniform float uWindPh;   // fase do vento (integral)
uniform float uRoll;
uniform float uZoom;
uniform float uGlow;     // brilho interno/tempestade

void main(){
  vec2 frag = gl_FragCoord.xy;
  vec2 p = rot2(uRoll)*((frag - .5*uRes)/(.5*uRes.x))/uZoom + uShake;

  // vórtice gigante
  vec2 sp = p - uSwirlC;
  float sr = length(sp);
  float tw = uSwirl*exp(-sr*sr*.9)*(1.+.25*sin(uT*.7));
  sp = rot2(tw + uSwirl*.15*uT*.3)*sp;
  vec2 pp = sp + uSwirlC;

  // céu de fundo
  float v = clamp(frag.y/uRes.y, 0., 1.);
  vec3 top = vec3(.004,.02,.10), mid = vec3(.02,.17,.55), low = vec3(.08,.45,.85);
  vec3 col = mix(low, mid, smoothstep(.0,.55,v));
  col = mix(col, top, smoothstep(.45,1.,v));
  // luz da estrela (contra-luz quente no alto à direita)
  vec2 sunP = vec2(.75,1.25);
  float ds = length(p - sunP);
  col += vec3(1.,.65,.38)*(.07/(ds*ds+.08));
  col += vec3(.2,.5,1.)*.35*exp(-length(p-vec2(-.2,-1.))*.9);
  col *= (1.-uDark);

  const int NL = 8;
  float x = uBase;
  float s = fract(x);
  float fl = floor(x);
  for(int jj=0; jj<NL; jj++){
    int j = NL-1-jj;               // do mais distante ao mais próximo
    float z = (s + float(j))/float(NL);
    float seed = float(j) - fl;
    float sd = hash11(seed*7.31)*100.;
    float persp = .35 + 2.6*z;
    vec2 uv = pp*persp;
    uv.x += uWindPh*(1.35-z) + sd;
    uv.y += sd*.37 + .08*sin(uT*.5+seed);
    vec2 sq = vec2(uv.x/uStretch, uv.y*1.25);
    float n  = fbm2(sq*.85, 6);
    float n2 = fbm2(sq*.85 + vec2(.06,.10), 6);
    float dens = smoothstep(.44,.70,n);
    float fade = smoothstep(.02,.22,z)*smoothstep(1.02,.55,z);
    float lightness = clamp((n2-n)*12.+.5, 0., 1.);
    vec3 shadow = vec3(.0,.025,.17);
    vec3 litc = vec3(.62,.88,1.);
    vec3 lc = mix(shadow, litc, lightness*.8 + .2*smoothstep(.55,.9,n));
    lc = mix(lc, vec3(.6,.9,1.), pow(lightness,3.)*.35);
    // névoa por profundidade
    lc = mix(lc, mid*1.1, smoothstep(.2,1.,z)*.6);
    // brilho interno da tempestade
    lc += vec3(.3,.55,1.)*uGlow*smoothstep(.55,.85,n)*.5;
    col = mix(col, lc, clamp(dens*fade*.95,0.,1.));
  }

  // relâmpago: ilumina nuvens por dentro
  float fm = fbm2(pp*1.3+vec2(uT*.2,0.),4);
  col += vec3(.45,.7,1.)*uFlash*(.35+1.2*fm);
  // bloom/luz volumétrica do alto
  col += vec3(.1,.3,.7)*pow(max(0.,1.-length(p-vec2(.5,1.1))*.45),3.)*.25;

  col = tonemap(col*1.05);
  col += (hash21(frag+uT*37.)-.5)/255.;
  outColor = vec4(col,1.);
}`;
