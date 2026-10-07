import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FieldCrop } from "@/features/review/components/FieldCrop";
import { cropRect } from "@/features/review/crop";
import type { ImageState } from "@/features/review/useImageSize";

const drawImage = vi.fn();
let image: HTMLImageElement;

beforeEach(() => {
  drawImage.mockClear();
  image = document.createElement("img");
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
    drawImage,
    clearRect: vi.fn(),
  } as unknown as CanvasRenderingContext2D);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function ready(): ImageState {
  return { status: "ready", width: 1000, height: 1400, image };
}

describe("FieldCrop", () => {
  it("draws the part of the page around the field, from the image already loaded", () => {
    render(<FieldCrop source={ready()} box={[400, 500, 120, 30]} label="Name" />);

    const rect = cropRect([400, 500, 120, 30], { width: 1000, height: 1400 });
    expect(drawImage).toHaveBeenCalledTimes(1);
    expect(drawImage.mock.calls[0]?.slice(0, 5)).toEqual([
      image,
      rect.x,
      rect.y,
      rect.width,
      rect.height,
    ]);
    expect(screen.getByRole("img", { name: "Name, as read from the page" })).toBeInTheDocument();
  });

  it("holds the same space while the page image is still loading", () => {
    render(<FieldCrop source={{ status: "loading" }} box={[400, 500, 120, 30]} label="Name" />);

    expect(screen.getByTestId("crop-slot")).toHaveAttribute("aria-busy", "true");
    expect(drawImage).not.toHaveBeenCalled();
  });

  it("says so when the page image could not be loaded", () => {
    render(<FieldCrop source={{ status: "failed" }} box={[400, 500, 120, 30]} label="Name" />);

    expect(screen.getByText("Image unavailable")).toBeInTheDocument();
  });

  it("says so when the engine gave no position for the field", () => {
    render(<FieldCrop source={ready()} box={null} label="Name" />);

    expect(screen.getByText("No position")).toBeInTheDocument();
    expect(drawImage).not.toHaveBeenCalled();
  });
});
