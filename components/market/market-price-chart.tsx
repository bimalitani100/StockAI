"use client";

import { type PointerEvent, useId, useMemo, useState } from "react";

import type { MarketHistory, MarketHistoryPoint, MarketRange } from "@/types/market";

const VIEWBOX_WIDTH = 1000;
const VIEWBOX_HEIGHT = 340;
const TOP_PADDING = 18;
const BOTTOM_PADDING = 24;

type ChartPoint = MarketHistoryPoint & { x: number; y: number };

function money(value: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

function pointLabel(timestamp: string, range: MarketRange): string {
  const date = new Date(timestamp);
  if (range === "1d") {
    return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  }
  if (range === "1w" || range === "1m") {
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function MarketPriceChart({ history }: { history: MarketHistory }) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const gradientId = `market-area-${useId().replaceAll(":", "")}`;
  const isPositive = history.change >= 0;

  const chart = useMemo(() => {
    if (!history.points.length) {
      return { points: [], linePath: "", areaPath: "", baselineY: 0 };
    }
    const prices = history.points.map((point) => point.price);
    const observedMin = Math.min(...prices, history.baseline_price);
    const observedMax = Math.max(...prices, history.baseline_price);
    const observedRange = observedMax - observedMin;
    const padding = observedRange > 0 ? observedRange * 0.08 : observedMax * 0.01 || 1;
    const minimum = observedMin - padding;
    const maximum = observedMax + padding;
    const priceRange = maximum - minimum;
    const drawableHeight = VIEWBOX_HEIGHT - TOP_PADDING - BOTTOM_PADDING;

    const points: ChartPoint[] = history.points.map((point, index) => ({
      ...point,
      x: history.points.length === 1
        ? VIEWBOX_WIDTH / 2
        : (index / (history.points.length - 1)) * VIEWBOX_WIDTH,
      y: TOP_PADDING + ((maximum - point.price) / priceRange) * drawableHeight,
    }));
    const linePath = points.map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
    const areaPath = `${linePath} L${VIEWBOX_WIDTH},${VIEWBOX_HEIGHT} L0,${VIEWBOX_HEIGHT} Z`;
    const baselineY = TOP_PADDING + ((maximum - history.baseline_price) / priceRange) * drawableHeight;

    return { points, linePath, areaPath, baselineY };
  }, [history]);

  const selectedPoint = selectedIndex === null ? null : chart.points[selectedIndex];
  const lastPoint = chart.points.at(-1);

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    const relativeX = Math.min(Math.max(event.clientX - bounds.left, 0), bounds.width);
    const ratio = bounds.width ? relativeX / bounds.width : 0;
    setSelectedIndex(Math.round(ratio * (chart.points.length - 1)));
  }

  if (!history.points.length) {
    return <p className="chart-empty">No chart points are available for this range.</p>;
  }

  return (
    <div className={`market-chart ${isPositive ? "chart-positive" : "chart-negative"}`}>
      <div
        className="chart-canvas"
        onPointerMove={handlePointerMove}
        onPointerLeave={() => setSelectedIndex(null)}
      >
        <svg
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={`${history.company_name} ${history.range.toUpperCase()} price chart`}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.22" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
            </linearGradient>
          </defs>
          <line className="chart-baseline" x1="0" x2={VIEWBOX_WIDTH} y1={chart.baselineY} y2={chart.baselineY} vectorEffect="non-scaling-stroke" />
          <path className="chart-area" d={chart.areaPath} fill={`url(#${gradientId})`} />
          <path className="chart-line" d={chart.linePath} vectorEffect="non-scaling-stroke" />
          {selectedPoint && <line className="chart-crosshair" x1={selectedPoint.x} x2={selectedPoint.x} y1="0" y2={VIEWBOX_HEIGHT} vectorEffect="non-scaling-stroke" />}
        </svg>

        {lastPoint && (
          <span
            className="chart-live-dot"
            style={{ left: `${(lastPoint.x / VIEWBOX_WIDTH) * 100}%`, top: `${(lastPoint.y / VIEWBOX_HEIGHT) * 100}%` }}
          />
        )}

        {selectedPoint && (
          <div
            className="chart-tooltip"
            style={{
              left: `${(selectedPoint.x / VIEWBOX_WIDTH) * 100}%`,
              top: `${(selectedPoint.y / VIEWBOX_HEIGHT) * 100}%`,
              transform: selectedPoint.x > VIEWBOX_WIDTH * 0.78 ? "translate(-100%, -118%)" : "translate(12px, -118%)",
            }}
          >
            <strong>{money(selectedPoint.price, history.currency)}</strong>
            <span>{pointLabel(selectedPoint.timestamp, history.range)}</span>
          </div>
        )}
      </div>

      <div className="chart-axis" aria-hidden="true">
        <span>{pointLabel(history.points[0].timestamp, history.range)}</span>
        <span>{pointLabel(history.points[Math.floor((history.points.length - 1) / 2)].timestamp, history.range)}</span>
        <span>{pointLabel(history.points.at(-1)!.timestamp, history.range)}</span>
      </div>
    </div>
  );
}
