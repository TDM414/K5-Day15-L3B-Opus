const steps = [
  ["Nhập yêu cầu", "Dán tin nhắn nhóm để mình đọc món muốn ăn, điều kiêng và ngân sách."],
  ["Xác nhận", "Kiểm lại điều kiêng và ngân sách từng người trước khi tìm quán."],
  ["Chọn quán", "So sánh giá món và phí ship rồi chọn một quán cho cả nhóm."],
  ["Chốt giỏ", "Xem lại món và tổng tiền từng người, rồi chốt khi cả nhóm đã thống nhất."],
];
const example = "Mai: muốn ăn cơm gà, 75k\nAn: ăn chay, không cay, 65k\nLinh: ăn gì cũng được, 70k";
const draftPlaceholder = [
  "Ghi tên, món muốn ăn, điều kiêng và ngân sách nếu có. Có thể dán nguyên tin nhắn nhóm.",
  "Ví dụ:",
  "Mai: cơm gà, 75k",
  "An: ăn chay, 65k",
].join("\n");
const state = {
  step: 0, text: "", budget: "", parsed: "", members: [], restaurants: [], restaurant: null, draftId: null, revision: null,
  options: [], menu: [], menuOpen: false, editingMember: null, selections: [], cart: null, cartNotices: [], swap: null, changed: new Set(),
  busy: "", errors: {}, notice: "", status: "", finalized: false, copyFeedback: null, guide: true, saveProfiles: false,
  profiles: [], history: [], savedLoaded: false, savedNotice: "", preferredRestaurantId: null, confirmedMembers: "",
  swapFeedback: "", replacement: "", retry: null,
};
const content = document.querySelector("#step-content");
const title = document.querySelector("#step-title");
const guide = document.querySelector("#guide");
const guideToggle = document.querySelector("#guide-toggle");
const announcement = document.querySelector("#announcement");
const currency = new Intl.NumberFormat("vi-VN");
const money = value => currency.format(value) + "đ";
const menuPrice = value => Number.isSafeInteger(value) ? money(value) : "Chưa có giá";
const escape = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[char]);
function menuPhoto(url, kind) {
  if (typeof url !== "string" || !/^\/assets\/menu\/[a-z0-9-]+\.webp$/.test(url)) return "";
  const restaurant = kind === "restaurant-photo" || kind === "cart-restaurant-photo";
  return `<img class="menu-photo ${kind}" src="${escape(url)}" alt="" width="${restaurant ? 480 : 320}" height="${restaurant ? 360 : 320}" loading="lazy" decoding="async">`;
}

const normalize = value => value.toLocaleLowerCase("vi").normalize("NFD").replace(/\p{M}/gu, "").replaceAll("đ", "d");
const emptyMember = () => ({
  name: "", budget: "", allergies: "", avoid: "", wants: "", vegetarian: false, blind: true, dishRequired: false,
});
const inputMoney = value => {
  const compact = value.trim().toLowerCase().replace(/[.\s]/g, "");
  const match = compact.match(/^(\d+)(k|đ|₫|vnd)?$/);
  if (!match) return null;
  const amount = Number(match[1]) * (match[2] === "k" ? 1000 : 1);
  return Number.isSafeInteger(amount) && amount > 0 ? amount : null;
};

function memberFromApi(member, budget = "") {
  const person = {
    name: member.name,
    budget: member.budget_vnd ? String(member.budget_vnd) : budget,
    allergies: (member.allergies || []).join(", "),
    avoid: [...new Set([
      ...(member.avoid_keywords || []), ...(member.avoid_allergens || []),
      ...(member.require_non_vegetarian ? ["chay"] : []),
    ])].join(", "),
    wants: member.requested_dish || member.preferred_dish || "",
    vegetarian: Boolean(member.vegetarian),
    dishRequired: Boolean(member.dish_required),
  };
  person.blind = !person.dishRequired && (Boolean(member.blind_bag) || !memberRequirements(person).length);
  person.explicitBlind = Boolean(member.blind_bag);
  return person;
}

function membersForCheck() {
  return state.members.map(member => ({
    name: member.name.trim(),
    budget_vnd: inputMoney(member.budget),
    vegetarian: member.vegetarian,
    avoid_keywords: member.avoid.split(/[,;]+/).map(term => term.trim()).filter(Boolean),
    allergies: member.allergies.split(/[,;]|\s+và\s+/i)
      .map(term => term.trim().replace(/^dị ứng\s+/i, "")).filter(Boolean),
    preferred_dish: member.blind && !member.dishRequired ? "" : member.wants.trim(),
    dish_required: member.dishRequired,
    blind_bag: member.blind && !member.dishRequired,
  }));
}

async function request(action, fields = {}) {
  const response = await fetch("/api/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, ...fields }),
    signal: AbortSignal.timeout(135_000),
  });
  const result = await response.json().catch(() => null);
  if (!response.ok || !result) {
    const error = new Error(result?.error || "Máy chủ chưa gửi được dữ liệu. Hãy thử lại.");
    error.code = result?.code || (response.status >= 500 || !result ? "retry" : "");
    error.draft = result?.draft;
    throw error;
  }
  return result;
}

function resetCart() {
  state.restaurant = null;
  state.cart = null;
  state.cartNotices = [];
  state.options = [];
  state.menu = [];
  state.menuOpen = false;
  state.selections = [];
  state.changed.clear();
  state.swap = null;
  state.finalized = false;
  state.copyFeedback = null;
  state.draftId = null;
  state.revision = null;
}

function navigate(step) {
  state.step = step;
  state.notice = "";
  state.status = "";
  state.copyFeedback = null;
  state.errors = {};
  state.swap = null;
  state.retry = null;
  render();
  title.focus();
  title.scrollIntoView({ block: "nearest" });
}

async function pending(message, action, retry = null) {
  if (state.busy) return;
  state.busy = message;
  state.notice = "";
  state.status = "";
  state.retry = null;
  announcement.textContent = message;
  render();
  try {
    await action();
  } catch (error) {
    const timedOut = ["AbortError", "TimeoutError"].includes(error.name);
    const disconnected = error instanceof TypeError;
    if (error.code === "draft_conflict") applyDraft(error.draft);
    if (["draft_missing", "draft_invalid"].includes(error.code)) {
      resetCart();
      navigate(2);
    }
    if (timedOut || disconnected || error.code === "retry") {
      state.retry = retry || (() => pending(message, action));
    }
    state.notice = timedOut ? "Máy chủ phản hồi quá lâu. Hãy thử lại."
      : disconnected ? "Không kết nối được máy chạy demo. Kiểm tra máy chủ rồi thử lại."
      : error.message;
  } finally {
    state.busy = "";
    render();
    if (state.notice) content.querySelector(".notice")?.focus();
  }
}

const button = (label, action, kind = "secondary", attrs = "") =>
  `<button class="button ${kind}" type="button" data-action="${action}" ${attrs}>${label}</button>`;
const textButton = (label, action, attrs = "") =>
  `<button class="text-button" type="button" data-action="${action}" ${attrs}>${label}</button>`;
const alert = (message, kind = "") =>
  `<p class="notice ${kind}" role="${kind === "error" ? "alert" : "status"}" tabindex="-1">${escape(message)}</p>`;
const fieldError = (id, message) => message ? `<p id="${id}-error" class="field-error">${escape(message)}</p>` : "";
const errorAttrs = (id, message) => message ? `aria-invalid="true" aria-describedby="${id}-error"` : "";

function renderInput() {
  const error = state.errors.text;
  const budgetError = state.errors.budget;
  return `
    <form data-form="read" novalidate>
      <div class="field">
        <div class="field-line"><label for="draft">Yêu cầu của nhóm</label>${textButton("Tải ví dụ", "example")}</div>
        <textarea class="control" id="draft" name="text" placeholder="${escape(draftPlaceholder)}" ${errorAttrs("draft", error)} maxlength="12000">${escape(state.text)}</textarea>
        ${fieldError("draft", error)}
      </div>
      <div class="field budget-field">
        <label for="common-budget">Ngân sách chung mỗi người</label>
        <input class="control" id="common-budget" name="budget" value="${escape(state.budget)}" inputmode="numeric" maxlength="24" placeholder="Ví dụ 70.000đ" ${budgetError ? errorAttrs("common-budget", budgetError) : 'aria-describedby="common-hint"'}>
        ${fieldError("common-budget", budgetError)}
        <p class="helper" id="common-hint">Không bắt buộc. Đã bao gồm phí ship.</p>
      </div>
      <div class="actions">${textButton("Nhập thủ công", "manual")}<button class="button primary" type="submit">Đọc yêu cầu</button></div>
    </form>
    <div id="saved-content">${renderSaved()}</div>`;
}

function renderSaved() {
  const profiles = state.profiles.map((profile, index) => {
    const details = memberRequirements(memberFromApi(profile)).join(" · ");
    return `<li><div><strong>${escape(profile.name)}</strong>
      ${details ? `<div class="helper">${escape(details)}</div>` : ""}</div>
      ${textButton("Dùng hồ sơ", "profile", `data-index="${index}" aria-label="Dùng hồ sơ của ${escape(profile.name)}"`)}</li>`;
  }).join("");
  return `<details class="source-draft profile-picker"><summary>Hồ sơ đã lưu${state.profiles.length ? ` (${state.profiles.length})` : ""}</summary>
    ${state.savedNotice ? `<div role="status" class="helper">${escape(state.savedNotice)} ${textButton("Tải lại", "reload-saved")}</div>` : ""}
    ${profiles ? `<ul>${profiles}</ul>` : !state.savedNotice ? `<div class="helper">${state.savedLoaded ? "Chưa có hồ sơ. Chọn lưu hồ sơ khi chốt giỏ để dùng cho bữa sau." : "Đang tải hồ sơ…"}</div>` : ""}
    </details>
    ${state.step === 0 && state.history.length ? `<details class="source-draft"><summary>Lịch sử giỏ đã chốt (${state.history.length})</summary>
      ${state.history.map(order => `<article><strong>${escape(order.restaurant_name)}</strong> · ${money(order.total_order_vnd)}<small> · ${escape(new Date(order.created_at).toLocaleString("vi-VN"))}</small><ul>${order.items.map(item => `<li>${escape(item.member_name)}: ${escape(item.dish_name)}</li>`).join("")}</ul></article>`).join("")}
    </details>` : ""}`;
}

function useProfile(profile) {
  const saved = memberFromApi(profile, state.budget);
  const sameName = name => name.trim().normalize("NFC").toLocaleLowerCase("vi");
  let index = state.members.findIndex(member => sameName(member.name) === sameName(saved.name));
  if (index >= 0) {
    const member = state.members[index];
    member.allergies = mergeTerms(member.allergies, saved.allergies);
    member.avoid = mergeTerms(member.avoid, saved.avoid);
    member.vegetarian ||= saved.vegetarian;
    if (!member.wants.trim() && !member.explicitBlind) member.wants = saved.wants;
    if (!member.explicitBlind && !saved.blind) member.blind = false;
    member.budget ||= saved.budget;
  } else {
    index = state.members.findIndex(member => !member.name.trim() && !memberRequirements(member).length &&
      !member.wants.trim() && !member.dishRequired);
    if (index < 0) index = state.members.length;
    saved.budget = state.members[index]?.budget || saved.budget;
    state.members[index] = saved;
  }
  state.editingMember = index;
  navigate(1);
  announcement.textContent = `Đã dùng hồ sơ của ${saved.name}.`;
  content.querySelector(`#member-${index}-${inputMoney(state.members[index].budget) ? "name" : "budget"}`).focus();
}

function mergeTerms(current, saved) {
  const terms = new Map();
  for (const term of [current, saved].join(",").split(/[,;]+/).map(value => value.trim()).filter(Boolean)) {
    const key = term.normalize("NFC").toLocaleLowerCase("vi");
    if (!terms.has(key)) terms.set(key, term);
  }
  return [...terms.values()].join(", ");
}

const saveProfilesChoice = () => `<label class="check-label"><input id="save-profiles" type="checkbox" ${state.saveProfiles ? "checked" : ""}> Lưu hồ sơ và lịch sử giỏ của nhóm trên máy này khi chốt giỏ (không bật thì không lưu gì)</label>`;

function memberField(index, key, label, placeholder = "") {
  const id = `member-${index}-${key}`;
  const error = state.errors[id];
  return `<div class="field"><label for="${id}">${label}</label>
    <input class="control" id="${id}" data-member="${index}" data-field="${key}" value="${escape(state.members[index][key])}" placeholder="${placeholder}" maxlength="${key === "budget" ? 24 : 160}" ${key === "budget" ? 'inputmode="numeric"' : ""} ${errorAttrs(id, error)}>
    ${fieldError(id, error)}</div>`;
}

function memberRequirements(member) {
  const wants = member.wants.trim();
  return [
    member.vegetarian ? "Ăn chay" : "",
    member.allergies.trim() ? `Dị ứng: ${member.allergies.trim()}` : "",
    member.avoid.trim() ? `Tránh: ${member.avoid.trim()}` : "",
    !member.blind && wants ? `${member.dishRequired ? "Chỉ chọn" : "Muốn ăn"}: ${wants}` : "",
  ].filter(Boolean);
}

const memberDisplayName = (member, index) => member.name.trim() || `Người ${index + 1}`;
const memberBudgetLabel = member => inputMoney(member.budget) ? money(inputMoney(member.budget)) : "Chưa có ngân sách";

function updateMemberOverview(index) {
  const member = state.members[index];
  const prefix = `#member-${index}`;
  content.querySelector(prefix + "-title").textContent = memberDisplayName(member, index);
  content.querySelector(prefix + "-budget-summary").textContent = memberBudgetLabel(member);
  const details = content.querySelector(prefix + "-requirements");
  details.textContent = memberRequirements(member).join(" · ");
  details.hidden = !details.textContent;
}

function renderMembers() {
  const rows = state.members.map((member, index) => {
    const id = `member-${index}`;
    const expanded = state.editingMember === index;
    const details = memberRequirements(member).join(" · ");
    const issue = ["name", "budget", "wants"].map(key => state.errors[`${id}-${key}`]).find(Boolean);
    return `<article class="member" aria-labelledby="${id}-title">
      <div class="member-overview">
        <div class="member-identity">
          <h3 id="${id}-title">${escape(memberDisplayName(member, index))}</h3>
          <p class="helper" id="${id}-requirements" ${details ? "" : "hidden"}>${escape(details)}</p>
          ${!expanded && issue ? `<p class="field-error">${escape(issue)}</p>` : ""}
        </div>
        <span class="member-budget money" id="${id}-budget-summary">${memberBudgetLabel(member)}</span>
        <label class="check-label member-blind">
          <input type="checkbox" data-member="${index}" data-field="blind" aria-describedby="${id}-title" ${member.blind ? "checked" : ""} ${member.dishRequired ? "disabled" : ""}>
          Ăn gì cũng được
        </label>
        ${textButton(expanded ? "Xong" : "Sửa", "edit-member", `data-index="${index}" aria-controls="${id}-details" aria-expanded="${expanded}" aria-describedby="${id}-title"`)}
      </div>
      <fieldset id="${id}-details" class="member-details" ${expanded ? "" : "hidden"}>
        <legend class="visually-hidden">Sửa thông tin của ${escape(memberDisplayName(member, index))}</legend>
        ${expanded ? `
          <div class="member-grid">
            ${memberField(index, "name", "Tên")}
            ${memberField(index, "budget", "Ngân sách gồm ship", "70.000đ")}
            ${member.blind ? "" : `
              ${memberField(index, "allergies", "Dị ứng", "Ví dụ đậu phộng, tôm")}
              ${memberField(index, "avoid", "Điều kiêng hoặc món không thích", "Ví dụ cay, thịt heo")}
              ${memberField(index, "wants", "Món muốn ăn", "Ví dụ cơm gà")}
            `}
          </div>
          <div class="member-actions">
            ${member.blind ? "" : `<div class="check-row">
              <label class="check-label"><input type="checkbox" data-member="${index}" data-field="vegetarian" ${member.vegetarian ? "checked" : ""}> Ăn chay</label>
              <label class="check-label"><input type="checkbox" data-member="${index}" data-field="dishRequired" ${member.dishRequired ? "checked" : ""}> Chỉ chọn món này</label>
            </div>`}
            ${state.members.length > 1 ? textButton("Xóa người", "remove", `data-index="${index}" aria-describedby="${id}-title"`) : ""}
          </div>
        ` : ""}
      </fieldset>
    </article>`;
  }).join("");
  return `<form data-form="members" novalidate>
    ${state.text.trim() ? `<details class="source-draft"><summary>Xem tin nhắn gốc</summary><p>${escape(state.text)}</p></details>` : ""}
    <div id="saved-content">${renderSaved()}</div>
    <div class="member-list-heading"><h3>Thành viên</h3><span class="helper">Ngân sách đã gồm ship</span></div>
    <div class="members">${rows}</div>
    ${textButton("+ Thêm người", "add")}
    ${saveProfilesChoice()}
    <div class="actions">${button("Quay lại", "back")}<button class="button primary" type="submit">Xác nhận và tìm quán</button></div>
  </form>`;
}

function menuPriceRange(min, max) {
  if (!Number.isSafeInteger(min) || !Number.isSafeInteger(max)) return "Chưa có giá";
  return min === max ? money(min) : `${money(min)}–${money(max)}`;
}

function renderRestaurants() {
  const rows = state.restaurants.map(restaurant => {
    const selected = state.restaurant?.restaurant_id === restaurant.restaurant_id;
    return `<article class="restaurant ${selected ? "selected" : ""}">
      ${menuPhoto(restaurant.image_url, "restaurant-photo")}
      <div class="restaurant-content">
        <h3>${escape(restaurant.name)}</h3>
        <p class="helper">${escape(restaurant.style)}</p>
        <dl class="restaurant-pricing">
          <div><dt>Giá món còn hàng</dt><dd class="money">${menuPriceRange(restaurant.price_min_vnd, restaurant.price_max_vnd)}</dd></div>
          <div><dt>Phí ship</dt>
            <dd class="money">${money(restaurant.shipping_fee_vnd)}/đơn</dd>
            <dd class="helper money">${money(restaurant.ship_per_person_vnd)}/người</dd>
          </div>
        </dl>
        <div class="restaurant-foot">${selected ? '<span class="status-tag">Đã chọn</span>' : ""}
          ${button(selected ? "Xem lại giỏ" : "Chọn quán này", "choose", "secondary", `data-id="${escape(restaurant.restaurant_id)}" aria-label="${selected ? "Xem lại giỏ" : "Chọn quán này"}: ${escape(restaurant.name)}"`)}</div>
      </div>
    </article>`;
  }).join("");
  return `<div class="cart-heading"><span class="status-tag">Menu mẫu</span>${rows ? '<span class="helper">Ảnh minh họa</span>' : ""}</div>
    ${rows ? `<div class="restaurant-list">${rows}</div>` : alert(
      membersForCheck().some(member => member.dish_required)
        ? "Chưa có quán đáp ứng món bắt buộc và các điều kiện của cả nhóm. Quay lại xác nhận để kiểm tra món muốn ăn, điều kiêng và ngân sách."
        : membersForCheck().some(member => member.allergies.length)
        ? "Chưa tìm được quán phù hợp. Với món thiếu thông tin dị ứng, cần xác nhận thành phần trước khi chọn."
        : "Chưa có quán nào đáp ứng đủ điều kiện và ngân sách của cả nhóm. Quay lại kiểm tra thông tin từng người."
    )}
    <div class="actions">${button("Quay lại xác nhận", "back")}</div>`;
}

function renderCopyFeedback(kind) {
  const feedback = state.copyFeedback;
  if (feedback?.kind !== kind) return "";
  if (feedback.status) return alert(feedback.status, "success");
  const label = kind === "menu" ? "Chọn và sao chép thực đơn" : "Chọn và sao chép danh sách";
  return `<div class="field">
    <label for="copy-fallback">${label}</label>
    <textarea id="copy-fallback" class="control copy-fallback" readonly>${escape(feedback.fallback)}</textarea>
  </div>`;
}

function renderVenueMenu() {
  if (!state.menu.length) return "";
  const rows = state.menuOpen ? state.menu.map(dish => `<li class="menu-dish">
      ${menuPhoto(dish.image_url, "menu-dish-photo")}
      <div class="menu-dish-info">
        <p class="menu-dish-name">${escape(dish.name)}</p>
        ${dish.in_stock ? "" : '<span class="helper">Hết hàng</span>'}
      </div>
      <span class="money">${menuPrice(dish.price)}</span>
    </li>`).join("") : "";
  return `<section class="venue-menu" aria-labelledby="venue-menu-heading">
    <div class="venue-menu-heading">
      <h3 id="venue-menu-heading">Thực đơn quán</h3>
      <div class="venue-menu-actions">
        ${textButton(state.menuOpen ? "Ẩn thực đơn" : "Hiện thực đơn", "toggle-menu", `aria-expanded="${state.menuOpen}" aria-controls="venue-menu-content"`)}
        ${button("Sao chép thực đơn", "copy-menu", "secondary")}
      </div>
    </div>
    ${renderCopyFeedback("menu")}
    <div id="venue-menu-content" ${state.menuOpen ? "" : "hidden"}>
      <p class="helper">Giá món chưa gồm phí ship.</p>
      <ul class="venue-menu-list">${rows}</ul>
    </div>
  </section>`;
}

function renderCart() {
  if (!state.cart) return `<div class="actions">${button("Quay lại chọn quán", "back")}</div>`;
  const rows = state.cart.items.map((item, index) => {
    const others = state.options[index].filter(dish => dish.id !== item.dish_id);
    let controls = "";
    if (!state.finalized) {
      if (state.swap === index) {
        controls = `<form class="swap-form" data-form="swap" data-index="${index}">
          <label class="field-label" for="replacement">Món thay thế cho ${escape(item.member_name)}</label>
          <select class="control" id="replacement" name="dish" required><option value="">Chọn món</option>
          ${others.map(dish => `<option value="${escape(dish.id)}" ${state.replacement === dish.id ? "selected" : ""}>${escape(dish.name)} · ${money(dish.price + item.ship_share_vnd)}</option>`).join("")}
          </select>
          <div class="replacement-preview" data-replacement-photo>${menuPhoto(others.find(dish => dish.id === state.replacement)?.image_url, "dish-photo")}</div>
          <label class="field-label" for="swap-feedback">Hoặc nói món muốn đổi</label>
          <input class="control" id="swap-feedback" name="feedback" value="${escape(state.swapFeedback)}" maxlength="300" placeholder="Ví dụ hôm nay mình muốn ăn gà không cay" ${errorAttrs("swap-feedback", state.errors.feedback)}>
          ${fieldError("swap-feedback", state.errors.feedback)}
          ${button("Để AI gợi ý", "ai-swap", "secondary", `data-index="${index}"`)}
          <div class="swap-actions"><button class="button secondary" type="submit">Kiểm và đổi món</button>${textButton("Hủy đổi", "cancel")}</div>
        </form>`;
      } else if (state.changed.has(item.member_name)) {
        controls = '<p class="helper">Đã dùng lượt đổi món</p>';
      } else if (others.length) {
        controls = textButton("Đổi món", "swap", `data-index="${index}" aria-label="Đổi món cho ${escape(item.member_name)}"`);
      } else {
        controls = '<p class="helper">Chưa có món thay thế phù hợp</p>';
      }
    }
    return `<article class="cart-row">
      <div class="cart-item">
        ${menuPhoto(item.image_url, "dish-photo")}
        <div class="cart-item-text">
          <div class="cart-head"><h3>${escape(item.member_name)}</h3>${item.is_blind_bag ? '<span class="status-tag">Túi mù</span>' : ""}</div>
          <p class="dish">${escape(item.ten_mon)}</p>
          ${item.kitchen_note ? `<p class="kitchen-note">Ghi chú quán: ${escape(item.kitchen_note)}</p>` : ""}
        </div>
      </div>
      <div class="cart-cost"><span class="money">${money(item.price_vnd)} + ${money(item.ship_share_vnd)} ship</span><strong class="money">${money(item.total_member_vnd)}</strong></div>
      ${controls ? `<div class="cart-controls ${state.swap === index ? "expanded" : ""}">${controls}</div>` : ""}
    </article>`;
  }).join("");
  return `<div class="cart-heading cart-heading-with-photo">
    <div class="cart-restaurant">
      ${menuPhoto(state.cart.restaurant_image_url, "cart-restaurant-photo")}
      <h3>${escape(state.cart.restaurant_name)}</h3>
    </div>
    <span class="status-tag success">Giỏ đã kiểm</span>
  </div>
    ${!state.finalized ? state.cartNotices.map(message => alert(message)).join("") : ""}
    ${!state.finalized ? saveProfilesChoice() : ''}
    ${state.finalized ? alert("Đã chốt giỏ. Sao chép danh sách để tự đặt trên ứng dụng giao đồ ăn.", "success") : ""}
    ${rows}
    ${state.status ? alert(state.status, "success") : ""}
    <div class="actions">
      ${state.finalized ? textButton("Tạo đơn mới", "restart") : textButton("Đổi quán", "back")}
      ${button(state.finalized ? "Sao chép danh sách" : "Sao chép tin nhắn nháp", "copy")}
      ${state.finalized ? "" : button("Chốt giỏ", "finalize", "primary")}
    </div>
    ${renderCopyFeedback("cart")}
    ${renderVenueMenu()}`;
}

function renderSummary() {
  const rows = [["Số người", state.members.length ? state.members.length + " người" : "Chưa nhập"]];
  const hasCurrentRequirements = state.confirmedMembers === JSON.stringify(membersForCheck());
  const cart = hasCurrentRequirements ? state.cart : null;
  rows.push(["Quán đã chọn", hasCurrentRequirements && state.restaurant?.name || "Chưa chọn"]);
  if (cart) {
    rows.push(["Tiền món", money(cart.total_food_vnd)], ["Phí ship", money(cart.shipping_fee_vnd)], ["Tổng đơn", money(cart.total_order_vnd)]);
  }
  const rounded = cart && cart.items.reduce((total, item) => total + item.total_member_vnd, 0) > cart.total_order_vnd;
  document.querySelector("#summary-content").innerHTML = `<dl>${rows.map(([label, value]) =>
    `<div class="summary-line ${label === "Tổng đơn" ? "total" : ""}"><dt>${label}</dt><dd>${escape(value)}</dd></div>`).join("")}</dl>
    ${rounded ? '<p class="summary-note">Phần ship từng người được làm tròn lên đến đồng.</p>' : ""}`;
}

function render() {
  title.textContent = steps[state.step][0];
  document.querySelector("#guide-text").textContent = steps[state.step][1];
  document.querySelector("#progress").innerHTML = steps.map(([label], index) =>
    `<li ${index === state.step ? 'aria-current="step"' : index < state.step ? 'class="passed"' : ""}>
      <span class="step-marker"><span class="step-number">${index + 1}</span>${label}</span>
    </li>`).join("");
  const notice = state.retry
    ? `<div class="notice error" tabindex="-1"><p role="alert">${escape(state.notice)}</p>${button("Thử lại", "retry")}</div>`
    : state.notice ? alert(state.notice, "error") : "";
  content.innerHTML = notice +
    (state.busy ? alert(state.busy) : "") +
    [renderInput, renderMembers, renderRestaurants, renderCart][state.step]();
  content.setAttribute("aria-busy", String(Boolean(state.busy)));
  if (state.busy) content.querySelectorAll("button, input, select, textarea").forEach(control => { control.disabled = true; });
  renderSummary();
}

function memberErrors() {
  const errors = {};
  const names = state.members.map(member => normalize(member.name.trim()));
  state.members.forEach((member, index) => {
    const field = key => `member-${index}-${key}`;
    if (!names[index]) errors[field("name")] = "Nhập tên để phân biệt suất của từng người.";
    else if (names.indexOf(names[index]) !== index) errors[field("name")] = "Tên bị trùng. Thêm họ hoặc biệt danh.";
    if (!inputMoney(member.budget)) errors[field("budget")] = "Nhập ngân sách đã gồm phí ship.";
    if (member.dishRequired && !member.wants.trim()) errors[field("wants")] = "Nhập tên món bắt buộc.";
  });
  return errors;
}

function openFirstMemberError() {
  const first = Object.keys(state.errors)[0];
  state.editingMember = first ? Number(first.split("-")[1]) : null;
}

async function readInput() {
  state.errors = {};
  if (!state.text.trim()) state.errors.text = "Dán tin nhắn nhóm hoặc chọn Nhập thủ công.";
  if (state.budget.trim() && !inputMoney(state.budget)) state.errors.budget = "Nhập số tiền, ví dụ 70.000đ.";
  if (Object.keys(state.errors).length) {
    render();
    content.querySelector("[aria-invalid]")?.focus();
    return;
  }
  const input = JSON.stringify([state.text, state.budget]);
  if (input === state.parsed) {
    navigate(1);
    return;
  }
  await pending("Đang đọc yêu cầu bằng AI…", async () => {
    const parsed = await request("parse", { text: state.text, shared_budget_vnd: inputMoney(state.budget) });
    if (parsed.intent === "refuse") {
      throw new Error("Hãy nhập yêu cầu chọn món trưa theo menu mẫu và các điều kiện ăn uống của nhóm.");
    }
    if (parsed.intent === "swap") {
      throw new Error("Để đổi một suất, mở giỏ đã kiểm và chọn Đổi món cạnh tên người đó.");
    }
    state.members = parsed.members.map(member => memberFromApi(member, state.budget));
    if (!state.members.length) state.members.push({ ...emptyMember(), budget: state.budget });
    state.parsed = input;
    state.preferredRestaurantId = parsed.restaurant_id;
    state.confirmedMembers = "";
    resetCart();
    navigate(1);
    state.errors = memberErrors();
    openFirstMemberError();
    if (parsed.intent === "clarify" && !Object.keys(state.errors).length) {
      state.notice = parsed.reason || "Kiểm lại món muốn ăn, điều kiêng và ngân sách trước khi tìm quán.";
    }
  }, readInput);
}

async function findRestaurants() {
  state.errors = memberErrors();
  if (Object.keys(state.errors).length) {
    openFirstMemberError();
    render();
    content.querySelector("[aria-invalid]")?.focus();
    return;
  }
  const members = membersForCheck();
  const confirmedMembers = JSON.stringify(members);
  if (confirmedMembers === state.confirmedMembers) {
    navigate(2);
    return;
  }
  await pending("Đang tìm quán phù hợp…", async () => {
    const result = await request("restaurants", { members });
    resetCart();
    state.confirmedMembers = confirmedMembers;
    state.restaurants = result.restaurants;
    if (state.preferredRestaurantId) state.restaurants.sort((a, b) => Number(b.restaurant_id === state.preferredRestaurantId) - Number(a.restaurant_id === state.preferredRestaurantId));
    navigate(2);
  }, findRestaurants);
}

function applyDraft(draft) {
  if (state.draftId !== draft.draft_id) state.menuOpen = false;
  state.cart = draft.cart;
  state.options = draft.options;
  state.menu = draft.menu || [];
  state.selections = draft.selections;
  state.draftId = draft.draft_id;
  state.revision = draft.revision;
  state.changed = new Set(draft.changed_members);
  state.cartNotices = draft.notices;
  state.finalized = draft.finalized;
  state.copyFeedback = null;
  state.swap = null;
}

async function chooseRestaurant(id) {
  if (state.restaurant?.restaurant_id === id && state.cart) {
    navigate(3);
    return;
  }
  await pending("Đang dựng và kiểm giỏ…", async () => {
    const draft = await request("options", { restaurant: id, members: membersForCheck() });
    state.restaurant = state.restaurants.find(restaurant => restaurant.restaurant_id === id);
    applyDraft(draft);
    navigate(3);
  });
}

async function replaceDish(index, id) {
  const memberName = state.selections[index]?.member_name;
  if (!memberName || !id || state.changed.has(memberName)) return;
  const selections = state.selections.map((selection, choice) => choice === index ? { ...selection, dish_id: id } : selection);
  await pending("Đang kiểm món thay thế…", async () => {
    applyDraft(await request("check", { draft_id: state.draftId, revision: state.revision, selections }));
    announcement.textContent = "Đã đổi món cho " + memberName + ".";
    state.status = announcement.textContent;
  }, () => replaceDish(index, state.replacement));
}

async function recommendSwap(index, feedback) {
  const memberName = state.selections[index]?.member_name;
  if (!memberName || state.changed.has(memberName)) return;
  if (!feedback.trim()) {
    state.errors.feedback = "Nhập lý do hoặc món muốn đổi sang.";
    state.notice = "";
    state.retry = null;
    render();
    content.querySelector("#swap-feedback").focus();
    return;
  }
  state.errors = {};
  await pending("AI đang tìm món thay thế rồi kiểm tra lại giỏ…", async () => {
    applyDraft(await request("swap", { draft_id: state.draftId, revision: state.revision, member_name: memberName, feedback }));
    announcement.textContent = "Đã đổi món theo yêu cầu cho " + memberName + ".";
    state.status = announcement.textContent;
  }, () => recommendSwap(index, state.swapFeedback));
}

async function finalizeCart() {
  await pending("Đang kiểm lại toàn bộ giỏ…", async () => {
    applyDraft(await request("finalize", { draft_id: state.draftId, revision: state.revision, save_profiles: state.saveProfiles }));
    announcement.textContent = "Đã chốt giỏ.";
  });
}

async function loadSaved() {
  try {
    const { members, orders } = await request("saved");
    state.profiles = members;
    state.history = orders;
    state.savedLoaded = true;
    state.savedNotice = "";
  } catch {
    state.savedNotice = "Chưa tải được hồ sơ và lịch sử.";
  }
  const saved = content.querySelector("#saved-content");
  if (saved) {
    const open = saved.querySelector(".profile-picker")?.open;
    const retryFocused = document.activeElement?.dataset.action === "reload-saved";
    saved.innerHTML = renderSaved();
    saved.querySelector(".profile-picker").open = Boolean(open);
    if (retryFocused) saved.querySelector(".profile-picker summary").focus();
  }
}

async function copyCart() {
  await copyText([
    `${state.finalized ? "Danh sách chốt" : "Giỏ nháp"} · ${state.cart.restaurant_name}`,
    ...state.cart.items.map(item => `${item.member_name}: ${item.ten_mon}${item.kitchen_note ? ` (${item.kitchen_note})` : ""} · ${money(item.total_member_vnd)} gồm ship`),
    `Phí ship: ${money(state.cart.shipping_fee_vnd)}/đơn · ${money(state.cart.ship_per_person_vnd)}/người`,
    `Tổng đơn: ${money(state.cart.total_order_vnd)}`,
  ], "cart");
}

async function copyVenueMenu() {
  if (!state.menu.length) return;
  await copyText([
    `Thực đơn · ${state.cart.restaurant_name}`,
    "Giá món chưa gồm phí ship.",
    ...state.menu.map(dish => `- ${dish.name} · ${menuPrice(dish.price)}${dish.in_stock ? "" : " (Hết hàng)"}`),
  ], "menu");
}

async function copyText(lines, kind) {
  const text = lines.join("\n");
  try {
    await navigator.clipboard.writeText(text);
    state.copyFeedback = { kind, status: kind === "menu" ? "Đã sao chép thực đơn." : "Đã sao chép danh sách." };
    render();
    content.querySelector(kind === "menu" ? '[data-action="copy-menu"]' : '[data-action="copy"]')?.focus();
  } catch {
    state.copyFeedback = { kind, fallback: text };
    render();
    const field = content.querySelector("#copy-fallback");
    field.focus();
    field.select();
  }
}

guideToggle.addEventListener("click", () => {
  state.guide = !state.guide;
  guide.hidden = !state.guide;
  guideToggle.setAttribute("aria-expanded", String(state.guide));
  guideToggle.textContent = state.guide ? "Ẩn hướng dẫn" : "Hiện hướng dẫn";
});

content.addEventListener("error", event => {
  if (event.target.matches("img.menu-photo")) event.target.hidden = true;
}, true);

content.addEventListener("input", event => {
  const field = event.target;
  if (field.id === "save-profiles") {
    state.saveProfiles = field.checked;
  } else if (field.dataset.member !== undefined) {
    const index = Number(field.dataset.member);
    const key = field.dataset.field;
    state.members[index][key] = field.type === "checkbox" ? field.checked : field.value;
    if (key === "blind" || key === "dishRequired") {
      if (key === "blind") state.members[index].explicitBlind = field.checked;
      if (key === "blind" && !field.checked) state.editingMember = index;
      render();
      content.querySelector(`[data-member="${index}"][data-field="${key}"]`)?.focus();
    } else {
      updateMemberOverview(index);
      renderSummary();
    }
  } else if (field.name === "text" || field.name === "budget") {
    state[field.name] = field.value;
  } else if (field.name === "feedback") {
    state.swapFeedback = field.value;
  } else if (field.name === "dish") {
    state.replacement = field.value;
    const options = state.options[Number(field.form.dataset.index)] || [];
    const dish = options.find(option => option.id === field.value);
    field.form.querySelector("[data-replacement-photo]").innerHTML = menuPhoto(dish?.image_url, "dish-photo");
  }
});

content.addEventListener("submit", async event => {
  event.preventDefault();
  if (state.busy) return;
  const form = event.target;
  switch (form.dataset.form) {
    case "read": await readInput(); break;
    case "members": await findRestaurants(); break;
    case "swap": await replaceDish(Number(form.dataset.index), new FormData(form).get("dish")); break;
  }
});

content.addEventListener("click", async event => {
  const target = event.target.closest("[data-action]");
  if (!target || state.busy) return;
  const index = Number(target.dataset.index);
  switch (target.dataset.action) {
    case "example":
      state.text = example;
      state.errors = {};
      render();
      content.querySelector("#draft").focus();
      break;
    case "profile": {
      const profile = state.profiles[index];
      if (profile) useProfile(profile);
      break;
    }
    case "reload-saved": await loadSaved(); break;
    case "retry": await state.retry?.(); break;
    case "manual":
      if (!state.members.length) state.members.push({ ...emptyMember(), budget: state.budget });
      state.editingMember ??= 0;
      navigate(1);
      break;
    case "back":
      navigate(state.step - 1);
      break;
    case "add":
      state.members.push({ ...emptyMember(), budget: state.budget });
      state.editingMember = state.members.length - 1;
      render();
      content.querySelector(`#member-${state.editingMember}-name`).focus();
      break;
    case "edit-member":
      state.editingMember = state.editingMember === index ? null : index;
      render();
      content.querySelector(`[data-action="edit-member"][data-index="${index}"]`)?.focus();
      break;
    case "remove":
      state.members.splice(index, 1);
      state.editingMember = null;
      state.errors = {};
      render();
      content.querySelector(`[data-action="edit-member"][data-index="${Math.min(index, state.members.length - 1)}"]`)?.focus();
      break;
    case "choose": await chooseRestaurant(target.dataset.id); break;
    case "swap":
      state.swap = index;
      state.swapFeedback = "";
      state.replacement = "";
      state.errors = {};
      render();
      content.querySelector("#replacement").focus();
      break;
    case "cancel":
      const swapIndex = state.swap;
      state.swap = null;
      state.notice = "";
      state.retry = null;
      render();
      content.querySelector(`[data-action="swap"][data-index="${swapIndex}"]`)?.focus();
      break;
    case "ai-swap": {
      await recommendSwap(index, state.swapFeedback);
      break;
    }
    case "copy": await copyCart(); break;
    case "copy-menu": await copyVenueMenu(); break;
    case "toggle-menu":
      state.menuOpen = !state.menuOpen;
      render();
      content.querySelector('[data-action="toggle-menu"]')?.focus();
      break;
    case "finalize": await finalizeCart(); break;
    case "restart":
      resetCart();
      state.text = "";
      state.budget = "";
      state.parsed = "";
      state.members = [];
      state.editingMember = null;
      state.restaurants = [];
      state.confirmedMembers = "";
      state.preferredRestaurantId = null;
      state.saveProfiles = false;
      navigate(0);
      await loadSaved();
      break;
  }
});

render();
loadSaved();
