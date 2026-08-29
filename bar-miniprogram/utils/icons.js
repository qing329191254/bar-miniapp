const SVG = {
  order: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M6 4h12l2 4v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8z"/><path d="M4 8h16"/><path d="M8 12h8M8 16h5"/></svg>',
  card: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/><path d="M7 15h4"/></svg>',
  point: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M12 2l2.9 6.9L22 10l-5.5 4.7L18 22l-6-3.6L6 22l1.5-7.3L2 10l7.1-1.1z"/></svg>',
  sign: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 12l3 3 5-6"/></svg>',
  play: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="9" cy="9" r="1" fill="white" stroke="none"/><circle cx="15" cy="15" r="1" fill="white" stroke="none"/><circle cx="15" cy="9" r="1" fill="white" stroke="none"/><circle cx="9" cy="15" r="1" fill="white" stroke="none"/></svg>',
  recharge: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="8"/><path d="M12 8v8M9 11h6"/></svg>',
  shop: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M12 21s7-4.5 7-10a7 7 0 1 0-14 0c0 5.5 7 10 7 10z"/><circle cx="12" cy="11" r="2.5"/></svg>',
  faq: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 4.2 1.8c-.8.7-1.7 1.2-1.7 2.7"/><circle cx="12" cy="17" r=".8" fill="white" stroke="none"/></svg>',
  terms: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M8 4h8l4 4v12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M16 4v4h4M10 12h6M10 16h6"/></svg>',
  privacy: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M12 3l7 3v6c0 4.5-3.2 8.2-7 9-3.8-.8-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/></svg>',
  deact: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M12 9v4M12 17h.01"/><path d="M10.3 4.5h3.4L22 12l-8.3 7.5h-3.4L2 12z"/></svg>',
  coin: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="8"/><path d="M12 8v8M9.5 10.5h5M9.5 13.5h5"/></svg>',
  shard: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M12 2l3.5 6.5L22 10l-5 5.2L18.5 22 12 18.8 5.5 22 7 15.2 2 10l6.5-1.5z" opacity=".95"/></svg>',
  trophy: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M8 4h8v3a4 4 0 0 1-8 0z"/><path d="M6 4H4v2a3 3 0 0 0 3 3M18 4h2v2a3 3 0 0 1-3 3"/><path d="M12 11v3M9 20h6M10 14h4v3H10z"/></svg>',
  team: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 19c0-3 2.7-5 6-5s6 2 6 5M14 19c0-2.2 1.8-4 4-4"/></svg>',
  accept: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M5 6h14l-2 12H7z"/><path d="M9 6V4h6v2"/></svg>',
  pay: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/></svg>',
  wdr: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M7 7h10v10H7z"/><path d="M11 12h2M4 12h3M17 12h3M12 4v3M12 17v3"/></svg>',
  making: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M6 3v7M12 3v7M18 3v7"/><path d="M4 10h16v4H4z"/><path d="M7 18h10"/></svg>',
  verify: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M4 7h16v12H4z"/><path d="M8 7V5h8v2"/><path d="M9 13l2 2 4-4"/></svg>',
  game: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><rect x="3" y="8" width="18" height="10" rx="4"/><circle cx="8.5" cy="13" r="1.2" fill="white" stroke="none"/><path d="M14 11v4M12 13h4"/></svg>',
  scan: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4"/><rect x="7" y="7" width="10" height="10" rx="1"/></svg>',
  bell: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M12 4a4 4 0 0 0-4 4v4l-2 3h12l-2-3v-4a4 4 0 0 0-4-4z"/><path d="M10 20h4"/></svg>',
  chart: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M4 19V5M4 19h16"/><path d="M8 15v-4M12 15V8M16 15v-6"/></svg>',
  grant: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M12 3v18"/><path d="M5 8h14M7 12h10"/></svg>',
  rank: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M7 20V10M12 20V4M17 20v-7"/></svg>',
  chevron: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#9C9A93" stroke-width="2.2" stroke-linecap="round"><path d="M9 6l6 6-6 6"/></svg>',
};

export const GRAD = {
  teal: "linear-gradient(135deg,#2FAF8F,#7EDFC4)",
  blue: "linear-gradient(135deg,#3B82D9,#8BBEF5)",
  pink: "linear-gradient(135deg,#D96A96,#F4B8CE)",
  green: "linear-gradient(135deg,#6FAF3E,#B8DD88)",
  purple: "linear-gradient(135deg,#7B72E8,#C5C0FA)",
  gold: "linear-gradient(135deg,#E89A3C,#FAC775)",
  indigo: "linear-gradient(135deg,#534AB7,#9A93E8)",
  amber: "linear-gradient(135deg,#BA7517,#E8B45A)",
  slate: "linear-gradient(135deg,#2C2924,#5C564E)",
  red: "linear-gradient(135deg,#C94A4A,#F08A8A)",
  staff: "linear-gradient(135deg,#1A2332,#2E4566 55%,#3D5F8C)",
};

export function iconSrc(name) {
  const svg = SVG[name];
  if (!svg) return "";
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

export function iconNames() {
  return Object.keys(SVG);
}
