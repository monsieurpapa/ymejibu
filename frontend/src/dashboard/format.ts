const nf = (d: number) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: d, minimumFractionDigits: 0 });

export const fmt = {
  pct: (v: number) => `${nf(1).format(v * 100)} %`,
  int: (v: number) => nf(0).format(v),
  num: (v: number) => nf(1).format(v),
  dec3: (v: number) => nf(3).format(v),
  usd: (v: number) => `${nf(0).format(v)} USD`,
  usd3: (v: number) => `${nf(3).format(v)} USD`,
  h: (v: number) => `${nf(1).format(v)} h`,
  m3: (v: number) => `${nf(0).format(v)} m³`,
  kwh: (v: number) => `${nf(0).format(v)} kWh`,
  l: (v: number) => `${nf(0).format(v)} L`,
};

export type FmtKey = keyof typeof fmt;
