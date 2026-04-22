import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

export const RadialAnalytics = ({ percentage, label, color = "#06b6d4" }) => {
  const svgRef = useRef();

  useEffect(() => {
    const width = 150;
    const height = 150;
    const radius = Math.min(width, height) / 2;
    const innerRadius = radius * 0.7;

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .append("g")
      .attr("transform", `translate(${width / 2}, ${height / 2})`);

    const arc = d3.arc()
      .innerRadius(innerRadius)
      .outerRadius(radius)
      .startAngle(0)
      .cornerRadius(10);

    // Background track
    svg.append("path")
      .datum({ endAngle: 2 * Math.PI })
      .style("fill", "rgba(255,255,255,0.05)")
      .attr("d", arc);

    // Progress arc
    const foreground = svg.append("path")
      .datum({ endAngle: 0 })
      .style("fill", color)
      .attr("d", arc);

    foreground.transition()
      .duration(1500)
      .ease(d3.easeCubicOut)
      .attrTween("d", (d) => {
        const interpolate = d3.interpolate(d.endAngle, (percentage / 100) * 2 * Math.PI);
        return (t) => {
          d.endAngle = interpolate(t);
          return arc(d);
        };
      });

    // Label
    svg.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", ".35em")
      .style("fill", "#fff")
      .style("font-size", "1.5rem")
      .style("font-weight", "bold")
      .text(`${percentage}%`);

  }, [percentage, color]);

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <svg ref={svgRef}></svg>
      <span className="mt-2 text-slate-500 text-sm font-medium uppercase tracking-wider">{label}</span>
    </div>
  );
};
