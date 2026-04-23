import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

export const RadialAnalytics = ({ percentage, label, color = "#4f46e5" }) => {
  const svgRef = useRef();

  useEffect(() => {
    d3.select(svgRef.current).selectAll("*").remove();

    const width = 140;
    const height = 140;
    const radius = Math.min(width, height) / 2;
    const innerRadius = radius * 0.75;

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .append("g")
      .attr("transform", `translate(${width / 2}, ${height / 2})`);

    const arc = d3.arc()
      .innerRadius(innerRadius)
      .outerRadius(radius)
      .startAngle(0)
      .cornerRadius(8);

    // Background track
    svg.append("path")
      .datum({ endAngle: 2 * Math.PI })
      .style("fill", "#f1f5f9")
      .attr("d", arc);

    // Progress arc
    const foreground = svg.append("path")
      .datum({ endAngle: 0 })
      .style("fill", color)
      .attr("d", arc);

    foreground.transition()
      .duration(1200)
      .ease(d3.easeCubicOut)
      .attrTween("d", (d) => {
        const interpolate = d3.interpolate(d.endAngle, (percentage / 100) * 2 * Math.PI);
        return (t) => {
          d.endAngle = interpolate(t);
          return arc(d);
        };
      });

    // Percentage Text
    svg.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .style("fill", "#0f172a")
      .style("font-size", "1.5rem")
      .style("font-weight", "900")
      .style("font-family", "Inter, sans-serif")
      .text(`${percentage}%`);

  }, [percentage, color]);

  return (
    <div className="flex flex-col items-center justify-center">
      <svg ref={svgRef}></svg>
      <span className="mt-2 text-slate-500 text-sm font-medium uppercase tracking-wider">{label}</span>
    </div>
  );
};
