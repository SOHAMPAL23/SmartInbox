import React from 'react';
import { 
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';

export const D3LineChart = React.memo(({ data, height = 300, color = "#4f46e5" }) => {
  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return [];
    return data.map((d, i) => ({ name: d.label || i, value: d.value }));
  }, [data]);

  return (
    <div style={{ width: '100%', height: height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis 
            dataKey="name" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            dy={10}
            interval="preserveStartEnd"
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            dx={-10}
            tickFormatter={(val) => Number.isInteger(val) ? val : val.toFixed(1)}
          />
          <Tooltip 
            contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            labelStyle={{ color: '#64748b', fontSize: '12px', fontWeight: 'bold' }}
            itemStyle={{ color: color, fontSize: '14px', fontWeight: 'bold' }}
            formatter={(value) => [Number(value).toFixed(4), "Value"]}
          />
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke={color} 
            strokeWidth={3} 
            dot={false} 
            activeDot={{ r: 6, strokeWidth: 0, fill: color }}
            animationDuration={1500}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
});

export const D3BarChart = React.memo(({ data, height = 300, color = "#4f46e5" }) => {
  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return [];
    return data.map((d, i) => ({ name: d.label || i, value: d.value }));
  }, [data]);

  return (
    <div style={{ width: '100%', height: height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis 
            dataKey="name" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            dy={10}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            dx={-10}
            tickFormatter={(val) => Number.isInteger(val) ? val : val.toFixed(1)}
          />
          <Tooltip 
            cursor={{ fill: '#f8fafc' }}
            contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            labelStyle={{ color: '#64748b', fontSize: '12px', fontWeight: 'bold' }}
            itemStyle={{ color: color, fontSize: '14px', fontWeight: 'bold' }}
            formatter={(value) => [Number(value).toFixed(4), "Weight"]}
          />
          <Bar 
            dataKey="value" 
            fill={color} 
            radius={[4, 4, 4, 4]} 
            animationDuration={1500}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
});

export const D3DonutChart = React.memo(({ data, size = 200 }) => {
  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return [];
    return data.map((d) => ({ name: d.label, value: d.value }));
  }, [data]);

  const COLORS = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

  return (
    <div style={{ width: '100%', height: '100%', minHeight: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip 
            contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            itemStyle={{ fontSize: '14px', fontWeight: 'bold' }}
            formatter={(value) => [Number(value).toFixed(2), "Value"]}
          />
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius="65%"
            outerRadius="85%"
            paddingAngle={2}
            dataKey="value"
            animationDuration={1500}
            stroke="none"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
});
