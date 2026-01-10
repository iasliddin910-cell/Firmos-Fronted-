import { readStore } from "./tax.store";

function citationsText() {
  const s = readStore();
  // show last few citations as reference text helper (not fabrication)
  const last = s.legal_citations.slice(-5).map((c) => `- ${c.citation_label}`);
  return last.length ? last.join("\n") : "- (Hozircha registry’da citation yo‘q)";
}

export function taxChatReply(message: string) {
  const s = readStore();
  const hasSources = s.legal_sources.length > 0;

  const HOLAT = `Sizning savol: "${message}"\n` +
    `Hozirgi holat: Tax Optimizer maslahat beradi, lekin hisobot yubormaydi va kabinetga kirmaydi.`;

  const QONUNIY_ASOS = hasSources
    ? `Rasmiy manbalar registry’dan topilgan citation’lar:\n${citationsText()}`
    : `Rasmiy manbalar (legal_sources) registry bo‘sh. Qonuniy asos ko‘rsatish uchun avval rasmiy manbani kiriting.`;

  const OQIBAT = `Agar bu masala bo‘yicha qaror qabul qilinadigan bo‘lsa, avval rasmiy modda/band asosida tekshiruv qiling.\n` +
    `Eslatma: bu maslahat xarakterida. Buxgalter/yurist bilan tasdiqlang.`;

  return {
    format: "TAX_CHAT_3_SECTION",
    sections: [
      { title: "HOLAT", content: HOLAT },
      { title: "QONUNIY ASOS", content: QONUNIY_ASOS },
      { title: "OQIBAT / XAVF", content: OQIBAT }
    ],
    disclaimer: "Advice only. Confirm with accountant."
  };
}
