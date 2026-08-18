import { INSTANCE_STRIDE, type VolumeScene } from "./affordanceVolume";

export type VoxelBackend = "webgpu" | "webgl2";

export type OrbitCamera = {
  azimuth: number;
  elevation: number;
  distance: number;
  targetY: number;
};

export type RendererSnapshot = {
  backend: VoxelBackend;
  solidInstances: number;
  fieldInstances: number;
  drawCalls: number;
};

type RenderBackend = {
  readonly kind: VoxelBackend;
  resize(width: number, height: number, pixelRatio: number): void;
  update(scene: VolumeScene): void;
  render(camera: OrbitCamera): void;
  snapshot(): RendererSnapshot;
  dispose(): void;
};

const CUBE_VERTICES = new Float32Array([
  -0.5, -0.5, -0.5, 0.5, -0.5, -0.5, 0.5, 0.5, -0.5, -0.5, 0.5, -0.5, -0.5,
  -0.5, 0.5, 0.5, -0.5, 0.5, 0.5, 0.5, 0.5, -0.5, 0.5, 0.5,
]);

const CUBE_INDICES = new Uint16Array([
  0, 1, 2, 0, 2, 3, 4, 6, 5, 4, 7, 6, 0, 4, 5, 0, 5, 1, 3, 2, 6, 3, 6, 7, 1, 5,
  6, 1, 6, 2, 0, 3, 7, 0, 7, 4,
]);

const INSTANCE_BYTES = INSTANCE_STRIDE * Float32Array.BYTES_PER_ELEMENT;

function normalize3(
  vector: readonly [number, number, number],
): [number, number, number] {
  const length = Math.hypot(vector[0], vector[1], vector[2]) || 1;
  return [vector[0] / length, vector[1] / length, vector[2] / length];
}

function cross3(
  a: readonly [number, number, number],
  b: readonly [number, number, number],
): [number, number, number] {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

function dot3(
  a: readonly [number, number, number],
  b: readonly [number, number, number],
): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function lookAt(
  eye: readonly [number, number, number],
  target: readonly [number, number, number],
): Float32Array {
  const z = normalize3([
    eye[0] - target[0],
    eye[1] - target[1],
    eye[2] - target[2],
  ]);
  const x = normalize3(cross3([0, 1, 0], z));
  const y = cross3(z, x);
  return new Float32Array([
    x[0],
    y[0],
    z[0],
    0,
    x[1],
    y[1],
    z[1],
    0,
    x[2],
    y[2],
    z[2],
    0,
    -dot3(x, eye),
    -dot3(y, eye),
    -dot3(z, eye),
    1,
  ]);
}

function perspective(aspect: number, near = 0.1, far = 400): Float32Array {
  const f = 1 / Math.tan((48 * Math.PI) / 360);
  return new Float32Array([
    f / aspect,
    0,
    0,
    0,
    0,
    f,
    0,
    0,
    0,
    0,
    far / (near - far),
    -1,
    0,
    0,
    (far * near) / (near - far),
    0,
  ]);
}

function multiply4(a: Float32Array, b: Float32Array): Float32Array {
  const out = new Float32Array(16);
  for (let column = 0; column < 4; column += 1) {
    for (let row = 0; row < 4; row += 1) {
      let value = 0;
      for (let index = 0; index < 4; index += 1) {
        value += (a[index * 4 + row] ?? 0) * (b[column * 4 + index] ?? 0);
      }
      out[column * 4 + row] = value;
    }
  }
  return out;
}

export function orbitViewProjection(
  camera: OrbitCamera,
  aspect: number,
): Float32Array {
  const horizontal = Math.cos(camera.elevation) * camera.distance;
  const eye: [number, number, number] = [
    Math.sin(camera.azimuth) * horizontal,
    camera.targetY + Math.sin(camera.elevation) * camera.distance,
    Math.cos(camera.azimuth) * horizontal,
  ];
  return multiply4(
    perspective(Math.max(0.1, aspect)),
    lookAt(eye, [0, camera.targetY, 0]),
  );
}

function compileShader(
  gl: WebGL2RenderingContext,
  type: number,
  source: string,
): WebGLShader {
  const shader = gl.createShader(type);
  if (!shader) throw new Error("WebGL shader allocation failed.");
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message =
      gl.getShaderInfoLog(shader) ?? "Unknown shader compilation failure";
    gl.deleteShader(shader);
    throw new Error(message);
  }
  return shader;
}

class WebGlVoxelBackend implements RenderBackend {
  readonly kind = "webgl2" as const;
  private readonly gl: WebGL2RenderingContext;
  private readonly program: WebGLProgram;
  private readonly vao: WebGLVertexArrayObject;
  private readonly instanceBuffer: WebGLBuffer;
  private readonly matrixLocation: WebGLUniformLocation;
  private width = 1;
  private height = 1;
  private solids = new Float32Array();
  private field = new Float32Array();

  constructor(private readonly canvas: HTMLCanvasElement) {
    const gl = canvas.getContext("webgl2", {
      antialias: true,
      alpha: false,
      depth: true,
      powerPreference: "high-performance",
    });
    if (!gl) throw new Error("WebGL2 is not available.");
    this.gl = gl;
    const vertexShader = compileShader(
      gl,
      gl.VERTEX_SHADER,
      `#version 300 es
      precision highp float;
      layout(location = 0) in vec3 aPosition;
      layout(location = 1) in vec3 iPosition;
      layout(location = 2) in vec3 iScale;
      layout(location = 3) in vec4 iColor;
      uniform mat4 uViewProjection;
      out vec4 vColor;
      void main() {
        vec3 world = aPosition * iScale + iPosition;
        gl_Position = uViewProjection * vec4(world, 1.0);
        vColor = iColor;
      }`,
    );
    const fragmentShader = compileShader(
      gl,
      gl.FRAGMENT_SHADER,
      `#version 300 es
      precision highp float;
      in vec4 vColor;
      out vec4 outColor;
      void main() {
        outColor = vColor;
      }`,
    );
    const program = gl.createProgram();
    if (!program) throw new Error("WebGL program allocation failed.");
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program) ?? "WebGL link failure");
    }
    this.program = program;
    const matrixLocation = gl.getUniformLocation(program, "uViewProjection");
    if (!matrixLocation) throw new Error("WebGL matrix uniform is missing.");
    this.matrixLocation = matrixLocation;

    const vao = gl.createVertexArray();
    const vertexBuffer = gl.createBuffer();
    const indexBuffer = gl.createBuffer();
    const instanceBuffer = gl.createBuffer();
    if (!vao || !vertexBuffer || !indexBuffer || !instanceBuffer) {
      throw new Error("WebGL voxel buffers could not be allocated.");
    }
    this.vao = vao;
    this.instanceBuffer = instanceBuffer;
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, CUBE_VERTICES, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 12, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, CUBE_INDICES, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, instanceBuffer);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 3, gl.FLOAT, false, INSTANCE_BYTES, 0);
    gl.vertexAttribDivisor(1, 1);
    gl.enableVertexAttribArray(2);
    gl.vertexAttribPointer(2, 3, gl.FLOAT, false, INSTANCE_BYTES, 12);
    gl.vertexAttribDivisor(2, 1);
    gl.enableVertexAttribArray(3);
    gl.vertexAttribPointer(3, 4, gl.FLOAT, false, INSTANCE_BYTES, 24);
    gl.vertexAttribDivisor(3, 1);
    gl.bindVertexArray(null);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
  }

  resize(width: number, height: number, pixelRatio: number) {
    this.width = Math.max(1, Math.floor(width * pixelRatio));
    this.height = Math.max(1, Math.floor(height * pixelRatio));
    if (
      this.canvas.width !== this.width ||
      this.canvas.height !== this.height
    ) {
      this.canvas.width = this.width;
      this.canvas.height = this.height;
    }
    this.gl.viewport(0, 0, this.width, this.height);
  }

  update(scene: VolumeScene) {
    this.solids = scene.solids;
    this.field = scene.field;
  }

  private draw(instances: Float32Array) {
    if (instances.length === 0) return;
    const gl = this.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.instanceBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, instances, gl.DYNAMIC_DRAW);
    gl.drawElementsInstanced(
      gl.TRIANGLES,
      CUBE_INDICES.length,
      gl.UNSIGNED_SHORT,
      0,
      instances.length / INSTANCE_STRIDE,
    );
  }

  render(camera: OrbitCamera) {
    const gl = this.gl;
    gl.clearColor(0.025, 0.055, 0.05, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.useProgram(this.program);
    gl.bindVertexArray(this.vao);
    gl.uniformMatrix4fv(
      this.matrixLocation,
      false,
      orbitViewProjection(camera, this.width / this.height),
    );
    gl.disable(gl.BLEND);
    gl.depthMask(true);
    this.draw(this.solids);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.depthMask(false);
    this.draw(this.field);
    gl.depthMask(true);
    gl.disable(gl.BLEND);
    gl.bindVertexArray(null);
  }

  snapshot(): RendererSnapshot {
    return {
      backend: this.kind,
      solidInstances: this.solids.length / INSTANCE_STRIDE,
      fieldInstances: this.field.length / INSTANCE_STRIDE,
      drawCalls: Number(this.solids.length > 0) + Number(this.field.length > 0),
    };
  }

  dispose() {
    this.gl.deleteBuffer(this.instanceBuffer);
    this.gl.deleteVertexArray(this.vao);
    this.gl.deleteProgram(this.program);
  }
}

type GpuBufferLike = { destroy(): void };
type GpuTextureLike = { createView(): unknown; destroy(): void };
type GpuRenderPassLike = {
  setPipeline(pipeline: GpuRenderPipelineLike): void;
  setBindGroup(index: number, group: unknown): void;
  setVertexBuffer(slot: number, buffer: GpuBufferLike): void;
  setIndexBuffer(buffer: GpuBufferLike, format: "uint16"): void;
  drawIndexed(indexCount: number, instanceCount: number): void;
  end(): void;
};
type GpuCommandEncoderLike = {
  beginRenderPass(descriptor: Record<string, unknown>): GpuRenderPassLike;
  finish(): unknown;
};
type GpuRenderPipelineLike = { getBindGroupLayout(index: number): unknown };
type GpuQueueLike = {
  writeBuffer(
    buffer: GpuBufferLike,
    offset: number,
    data: ArrayBufferView<ArrayBufferLike>,
  ): void;
  submit(commands: readonly unknown[]): void;
};
type GpuDeviceLike = {
  readonly queue: GpuQueueLike;
  createBuffer(descriptor: Record<string, unknown>): GpuBufferLike;
  createTexture(descriptor: Record<string, unknown>): GpuTextureLike;
  createShaderModule(descriptor: Record<string, unknown>): unknown;
  createRenderPipeline(
    descriptor: Record<string, unknown>,
  ): GpuRenderPipelineLike;
  createBindGroup(descriptor: Record<string, unknown>): unknown;
  createCommandEncoder(): GpuCommandEncoderLike;
};
type GpuAdapterLike = { requestDevice(): Promise<GpuDeviceLike> };
type GpuNavigatorLike = {
  requestAdapter(
    options?: Record<string, unknown>,
  ): Promise<GpuAdapterLike | null>;
  getPreferredCanvasFormat(): string;
};
type GpuCanvasContextLike = {
  configure(descriptor: Record<string, unknown>): void;
  getCurrentTexture(): GpuTextureLike;
};

const GPU_BUFFER_COPY_DST = 0x0008;
const GPU_BUFFER_INDEX = 0x0010;
const GPU_BUFFER_VERTEX = 0x0020;
const GPU_BUFFER_UNIFORM = 0x0040;
const GPU_TEXTURE_RENDER_ATTACHMENT = 0x0010;

class WebGpuVoxelBackend implements RenderBackend {
  readonly kind = "webgpu" as const;
  private readonly context: GpuCanvasContextLike;
  private readonly device: GpuDeviceLike;
  private readonly format: string;
  private readonly vertexBuffer: GpuBufferLike;
  private readonly indexBuffer: GpuBufferLike;
  private readonly uniformBuffer: GpuBufferLike;
  private readonly solidPipeline: GpuRenderPipelineLike;
  private readonly fieldPipeline: GpuRenderPipelineLike;
  private readonly bindGroup: unknown;
  private solidBuffer: GpuBufferLike;
  private fieldBuffer: GpuBufferLike;
  private solidCapacity = 1;
  private fieldCapacity = 1;
  private solidCount = 0;
  private fieldCount = 0;
  private depthTexture: GpuTextureLike | null = null;
  private width = 1;
  private height = 1;

  private constructor(
    private readonly canvas: HTMLCanvasElement,
    context: GpuCanvasContextLike,
    device: GpuDeviceLike,
    format: string,
  ) {
    this.context = context;
    this.device = device;
    this.format = format;
    this.vertexBuffer = device.createBuffer({
      size: CUBE_VERTICES.byteLength,
      usage: GPU_BUFFER_VERTEX | GPU_BUFFER_COPY_DST,
    });
    this.indexBuffer = device.createBuffer({
      size: CUBE_INDICES.byteLength,
      usage: GPU_BUFFER_INDEX | GPU_BUFFER_COPY_DST,
    });
    this.uniformBuffer = device.createBuffer({
      size: 64,
      usage: GPU_BUFFER_UNIFORM | GPU_BUFFER_COPY_DST,
    });
    this.solidBuffer = this.createInstanceBuffer(1);
    this.fieldBuffer = this.createInstanceBuffer(1);
    device.queue.writeBuffer(this.vertexBuffer, 0, CUBE_VERTICES);
    device.queue.writeBuffer(this.indexBuffer, 0, CUBE_INDICES);

    const shader = device.createShaderModule({
      code: `
      struct Uniforms { viewProjection: mat4x4<f32> };
      @group(0) @binding(0) var<uniform> uniforms: Uniforms;

      struct VertexInput {
        @location(0) position: vec3<f32>,
        @location(1) instancePosition: vec3<f32>,
        @location(2) instanceScale: vec3<f32>,
        @location(3) instanceColor: vec4<f32>,
      };
      struct VertexOutput {
        @builtin(position) position: vec4<f32>,
        @location(0) color: vec4<f32>,
      };
      @vertex
      fn vertexMain(input: VertexInput) -> VertexOutput {
        var output: VertexOutput;
        let world = input.position * input.instanceScale + input.instancePosition;
        output.position = uniforms.viewProjection * vec4<f32>(world, 1.0);
        output.color = input.instanceColor;
        return output;
      }
      @fragment
      fn fragmentMain(input: VertexOutput) -> @location(0) vec4<f32> {
        return input.color;
      }`,
    });
    const vertex = {
      module: shader,
      entryPoint: "vertexMain",
      buffers: [
        {
          arrayStride: 12,
          stepMode: "vertex",
          attributes: [{ shaderLocation: 0, offset: 0, format: "float32x3" }],
        },
        {
          arrayStride: INSTANCE_BYTES,
          stepMode: "instance",
          attributes: [
            { shaderLocation: 1, offset: 0, format: "float32x3" },
            { shaderLocation: 2, offset: 12, format: "float32x3" },
            { shaderLocation: 3, offset: 24, format: "float32x4" },
          ],
        },
      ],
    };
    const depthStencil = {
      depthWriteEnabled: true,
      depthCompare: "less-equal",
      format: "depth24plus",
    };
    this.solidPipeline = device.createRenderPipeline({
      layout: "auto",
      vertex,
      fragment: {
        module: shader,
        entryPoint: "fragmentMain",
        targets: [{ format }],
      },
      primitive: { topology: "triangle-list", cullMode: "back" },
      depthStencil,
    });
    this.fieldPipeline = device.createRenderPipeline({
      layout: "auto",
      vertex,
      fragment: {
        module: shader,
        entryPoint: "fragmentMain",
        targets: [
          {
            format,
            blend: {
              color: {
                srcFactor: "src-alpha",
                dstFactor: "one-minus-src-alpha",
                operation: "add",
              },
              alpha: {
                srcFactor: "one",
                dstFactor: "one-minus-src-alpha",
                operation: "add",
              },
            },
          },
        ],
      },
      primitive: { topology: "triangle-list", cullMode: "back" },
      depthStencil: { ...depthStencil, depthWriteEnabled: false },
    });
    this.bindGroup = device.createBindGroup({
      layout: this.solidPipeline.getBindGroupLayout(0),
      entries: [{ binding: 0, resource: { buffer: this.uniformBuffer } }],
    });
  }

  static async create(
    canvas: HTMLCanvasElement,
  ): Promise<WebGpuVoxelBackend | null> {
    const gpu = (navigator as Navigator & { gpu?: GpuNavigatorLike }).gpu;
    if (!gpu) return null;
    const adapter = await gpu.requestAdapter({
      powerPreference: "high-performance",
    });
    if (!adapter) return null;
    const device = await adapter.requestDevice();
    const context = canvas.getContext(
      "webgpu",
    ) as unknown as GpuCanvasContextLike | null;
    if (!context) return null;
    const format = gpu.getPreferredCanvasFormat();
    context.configure({ device, format, alphaMode: "opaque" });
    return new WebGpuVoxelBackend(canvas, context, device, format);
  }

  private createInstanceBuffer(capacity: number): GpuBufferLike {
    return this.device.createBuffer({
      size: Math.max(INSTANCE_BYTES, capacity * INSTANCE_BYTES),
      usage: GPU_BUFFER_VERTEX | GPU_BUFFER_COPY_DST,
    });
  }

  private upload(
    data: Float32Array,
    current: GpuBufferLike,
    capacity: number,
  ): { buffer: GpuBufferLike; capacity: number } {
    const count = data.length / INSTANCE_STRIDE;
    let buffer = current;
    let nextCapacity = capacity;
    if (count > capacity) {
      nextCapacity = 2 ** Math.ceil(Math.log2(Math.max(1, count)));
      current.destroy();
      buffer = this.createInstanceBuffer(nextCapacity);
    }
    if (data.length) this.device.queue.writeBuffer(buffer, 0, data);
    return { buffer, capacity: nextCapacity };
  }

  resize(width: number, height: number, pixelRatio: number) {
    this.width = Math.max(1, Math.floor(width * pixelRatio));
    this.height = Math.max(1, Math.floor(height * pixelRatio));
    if (
      this.canvas.width !== this.width ||
      this.canvas.height !== this.height
    ) {
      this.canvas.width = this.width;
      this.canvas.height = this.height;
      this.depthTexture?.destroy();
      this.depthTexture = this.device.createTexture({
        size: [this.width, this.height],
        format: "depth24plus",
        usage: GPU_TEXTURE_RENDER_ATTACHMENT,
      });
    }
  }

  update(scene: VolumeScene) {
    const solidUpload = this.upload(
      scene.solids,
      this.solidBuffer,
      this.solidCapacity,
    );
    this.solidBuffer = solidUpload.buffer;
    this.solidCapacity = solidUpload.capacity;
    this.solidCount = scene.solids.length / INSTANCE_STRIDE;
    const fieldUpload = this.upload(
      scene.field,
      this.fieldBuffer,
      this.fieldCapacity,
    );
    this.fieldBuffer = fieldUpload.buffer;
    this.fieldCapacity = fieldUpload.capacity;
    this.fieldCount = scene.field.length / INSTANCE_STRIDE;
  }

  render(camera: OrbitCamera) {
    if (!this.depthTexture) return;
    this.device.queue.writeBuffer(
      this.uniformBuffer,
      0,
      orbitViewProjection(camera, this.width / this.height),
    );
    const encoder = this.device.createCommandEncoder();
    const pass = encoder.beginRenderPass({
      colorAttachments: [
        {
          view: this.context.getCurrentTexture().createView(),
          clearValue: { r: 0.025, g: 0.055, b: 0.05, a: 1 },
          loadOp: "clear",
          storeOp: "store",
        },
      ],
      depthStencilAttachment: {
        view: this.depthTexture.createView(),
        depthClearValue: 1,
        depthLoadOp: "clear",
        depthStoreOp: "store",
      },
    });
    pass.setBindGroup(0, this.bindGroup);
    pass.setVertexBuffer(0, this.vertexBuffer);
    pass.setIndexBuffer(this.indexBuffer, "uint16");
    if (this.solidCount) {
      pass.setPipeline(this.solidPipeline);
      pass.setVertexBuffer(1, this.solidBuffer);
      pass.drawIndexed(CUBE_INDICES.length, this.solidCount);
    }
    if (this.fieldCount) {
      pass.setPipeline(this.fieldPipeline);
      pass.setVertexBuffer(1, this.fieldBuffer);
      pass.drawIndexed(CUBE_INDICES.length, this.fieldCount);
    }
    pass.end();
    this.device.queue.submit([encoder.finish()]);
  }

  snapshot(): RendererSnapshot {
    return {
      backend: this.kind,
      solidInstances: this.solidCount,
      fieldInstances: this.fieldCount,
      drawCalls: Number(this.solidCount > 0) + Number(this.fieldCount > 0),
    };
  }

  dispose() {
    this.vertexBuffer.destroy();
    this.indexBuffer.destroy();
    this.uniformBuffer.destroy();
    this.solidBuffer.destroy();
    this.fieldBuffer.destroy();
    this.depthTexture?.destroy();
  }
}

export class AdaptiveVoxelRenderer {
  private constructor(private readonly backend: RenderBackend) {}

  static async create(
    canvas: HTMLCanvasElement,
  ): Promise<AdaptiveVoxelRenderer> {
    try {
      const webgpu = await WebGpuVoxelBackend.create(canvas);
      if (webgpu) return new AdaptiveVoxelRenderer(webgpu);
    } catch {
      // WebGPU is opportunistic. A deterministic WebGL2 fallback remains mandatory.
    }
    return new AdaptiveVoxelRenderer(new WebGlVoxelBackend(canvas));
  }

  get kind(): VoxelBackend {
    return this.backend.kind;
  }

  resize(width: number, height: number, pixelRatio: number) {
    this.backend.resize(width, height, pixelRatio);
  }

  update(scene: VolumeScene) {
    this.backend.update(scene);
  }

  render(camera: OrbitCamera) {
    this.backend.render(camera);
  }

  snapshot(): RendererSnapshot {
    return this.backend.snapshot();
  }

  dispose() {
    this.backend.dispose();
  }
}
