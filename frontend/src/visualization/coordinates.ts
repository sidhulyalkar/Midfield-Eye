export type Point = { x: number; y: number };

export type PitchTransform = {
  toScreen(point: Point): Point;
  toPitch(point: Point): Point;
  metresToPixels(distanceM: number): number;
};

export function createPitchTransform({
  pitchLength,
  pitchWidth,
  viewportWidth,
  viewportHeight,
  padding = 0,
}: {
  pitchLength: number;
  pitchWidth: number;
  viewportWidth: number;
  viewportHeight: number;
  padding?: number;
}): PitchTransform {
  const usableWidth = Math.max(1, viewportWidth - 2 * padding);
  const usableHeight = Math.max(1, viewportHeight - 2 * padding);
  const scale = Math.min(usableWidth / pitchLength, usableHeight / pitchWidth);
  const offsetX = (viewportWidth - pitchLength * scale) / 2;
  const offsetY = (viewportHeight - pitchWidth * scale) / 2;
  return {
    toScreen: ({ x, y }) => ({
      x: offsetX + x * scale,
      y: offsetY + y * scale,
    }),
    toPitch: ({ x, y }) => ({
      x: (x - offsetX) / scale,
      y: (y - offsetY) / scale,
    }),
    metresToPixels: (distanceM) => distanceM * scale,
  };
}
