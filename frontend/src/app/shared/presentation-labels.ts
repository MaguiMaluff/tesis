export function statusLabel(status?: string | null): string {
  const labels: Record<string, string> = {
    active: 'Activo',
    inactive: 'Inactivo',
    open: 'Abierto',
    closed: 'Cerrado',
    pending: 'Pendiente',
    error: 'Con error',
  };

  return labels[String(status || '').toLowerCase()] || 'Sin estado';
}

export function riskLevelLabel(level?: string | null): string {
  const labels: Record<string, string> = {
    low: 'Bajo',
    medium: 'Medio',
    high: 'Alto',
    critical: 'Crítico',
  };

  return labels[String(level || '').toLowerCase()] || 'Bajo';
}

export function trendLabel(trend?: string | null): string {
  const labels: Record<string, string> = {
    stable: 'Estable',
    up: 'En aumento',
    down: 'En descenso',
  };

  return labels[String(trend || '').toLowerCase()] || 'Estable';
}

export function stageLabel(stage?: string | number | null, label?: string | null): string {
  if (label && !/^\d+$/.test(String(label))) {
    return label;
  }

  const labels: Record<string, string> = {
    '0': 'Sin señales',
    '1': 'Enganche',
    '2': 'Confianza',
    '3': 'Sexualización',
    '4': 'Explotación',
  };

  return labels[String(stage ?? '')] || label || 'Sin señales';
}
