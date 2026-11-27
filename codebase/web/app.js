const steps = [
  ["Nhập yêu cầu", "Dán tin nhắn nhóm để mình đọc món muốn ăn, điều kiêng và ngân sách."],
  ["Xác nhận", "Kiểm lại điều kiêng và ngân sách từng người trước khi tìm quán."],
  ["Chọn quán", "So sánh phí ship mỗi người rồi chọn một quán cho cả nhóm."],
  ["Chốt giỏ", "Xem lại món và tổng tiền từng người, rồi chốt khi cả nhóm đã thống nhất."],
];
const example = "Mai: muốn ăn cơm gà, 75k\nAn: ăn chay, không cay, 65k\nLinh: ăn gì cũng được, 70k";
const state = {
  step: 0, text: "", budget: "", parsed: "", members: [], restaurants: [], restaurant: null,
  options: [], selections: [], cart: null, swap: null, changed: new Set(),
  busy: "", errors: {}, notice: "", status: "", finalized: false, fallback: "", guide: true,
  recentDishes: new Map(),
};
const content = document.querySelector("#step-content");
const title = document.querySelector("#step-title");
const guide = document.querySelector("#guide");
const guideToggle = document.querySelector("#guide-toggle");
const announcement = document.querySelector("#announcement");
const currency = new Intl.NumberFormat("vi-VN");
const money = value => currency.format(value) + "đ";
const escape = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[char]);
const normalize = value => value.toLocaleLowerCase("vi").normalize("NFD").replace(/\p{M}/gu, "").replaceAll("đ", "d");
const emptyMember = () => ({ name: "", budget: "", avoid: "", wants: "", vegetarian: false, blind: false });
const inputMoney = value => {
  const compact = value.trim().toLowerCase().replace(/[.\s]/g, "");
  const match = compact.match(/^(\d+)(k|đ|₫|vnd)?$/);
  if (!match) return null;
  const amount = Number(match[1]) * (match[2] === "k" ? 1000 : 1);
  return Number.isSafeInteger(amount) && amount > 0 ? amount : null;
};

function readLine(line, sharedBudget) {
  const member = { ...emptyMember(), budget: sharedBudget };
  const match = line.match(/^\s*([^:：]+)[:：]\s*(.*)$/);
  if (!match) return { ...member, wants: line.trim() };
  member.name = match[1].trim();
  const wishes = [];
  const avoids = [];
  for (const fragment of match[2].split(/[,;]+/).map(part => part.trim()).filter(Boolean)) {
    const budgetPhrase = fragment.replace(/^(?:ngân sách|tối đa)\s*/i, "");
    const amount = fragment.match(/(?:^|\s)(\d[\d.]*\s*(?:k|đ|₫|vnd))$/i)?.[1];
    const budget = inputMoney(budgetPhrase) || (amount && inputMoney(amount));
    if (budget) member.budget = String(budget);
    const part = budget ? fragment.slice(0, fragment.lastIndexOf(amount || budgetPhrase)).trim() : fragment;
    if (!part || /^(ngân sách|tối đa)$/i.test(part)) continue;
    if (/^(ăn\s+)?chay$/i.test(part)) {
      member.vegetarian = true;
    } else if (/^(ăn\s+)?(gì|món gì)\s+cũng\s+được$/i.test(part)) {
      member.blind = true;
    } else if (/^(dị ứng|kiêng|không( thích| ăn)?)\s+/i.test(part)) {
      avoids.push(part.replace(/^(kiêng|không( thích| ăn)?)\s+/i, ""));
    } else {
      wishes.push(part.replace(/^muốn\s+(ăn\s+)?/i, ""));
    }
  }
  member.avoid = avoids.join(", ");
  member.wants = wishes.join(", ");
  return member;
}

function membersForCheck() {
  const allergyPrefix = /^dị ứng\s+/i;
  return state.members.map(member => {
    const terms = member.avoid.split(/[,;]+/).map(word => word.trim()).filter(Boolean);
    return {
      name: member.name.trim(),
      budget_vnd: inputMoney(member.budget),
      vegetarian: member.vegetarian,
      avoid_allergens: terms.filter(term => !allergyPrefix.test(term)),
      allergies: terms.filter(term => allergyPrefix.test(term))
        .flatMap(term => term.replace(allergyPrefix, "").split(/\s+và\s+/i)),
      preferred_dish: member.blind ? "" : member.wants.trim(),
    };
  });
}

async function request(action, fields = {}) {
  const response = await fetch("/api/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, members: membersForCheck(), ...fields }),
    signal: AbortSignal.timeout(10_000),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}

function resetCart() {
  state.restaurant = null;
  state.cart = null;
  state.options = [];
  state.selections = [];
  state.changed.clear();
  state.swap = null;
  state.finalized = false;
  state.fallback = "";
}

function navigate(step) {
  state.step = step;
  state.notice = "";
  state.status = "";
  state.errors = {};
  state.swap = null;
  render();
  title.focus();
  title.scrollIntoView({ block: "nearest" });
}

async function pending(message, action) {
  state.busy = message;
  state.notice = "";
  state.status = "";
  announcement.textContent = message;
  render();
  try {
    await action();
  } catch (error) {
    state.notice = error instanceof TypeError || ["AbortError", "TimeoutError"].includes(error.name)
      ? "Không kết nối được máy chạy demo. Kiểm tra máy chủ rồi thử lại."
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
        <div class="field-line"><label for="draft">Tin nhắn nhóm</label>${textButton("Tải ví dụ", "example")}</div>
        <textarea class="control" id="draft" name="text" placeholder="Mai: muốn ăn cơm gà, 75k&#10;An: ăn chay, không cay, 65k" ${error ? errorAttrs("draft", error) : 'aria-describedby="draft-hint"'} maxlength="12000">${escape(state.text)}</textarea>
        ${fieldError("draft", error)}
        <p class="helper" id="draft-hint">Bản thử đọc theo mẫu <strong>Tên: yêu cầu, ngân sách</strong>. Mỗi người một dòng.</p>
      </div>
      <div class="field budget-field">
        <label for="common-budget">Ngân sách chung mỗi người</label>
        <input class="control" id="common-budget" name="budget" value="${escape(state.budget)}" inputmode="numeric" maxlength="24" placeholder="Ví dụ 70.000đ" ${budgetError ? errorAttrs("common-budget", budgetError) : 'aria-describedby="common-hint"'}>
        ${fieldError("common-budget", budgetError)}
        <p class="helper" id="common-hint">Không bắt buộc. Đã bao gồm phí ship.</p>
      </div>
      <div class="actions">${textButton("Nhập thủ công", "manual")}<button class="button primary" type="submit">Đọc yêu cầu</button></div>
    </form>`;
}

function memberField(index, key, label, placeholder = "") {
  const id = `member-${index}-${key}`;
  const error = state.errors[id];
  return `<div class="field"><label for="${id}">${label}</label>
    <input class="control" id="${id}" data-member="${index}" data-field="${key}" value="${escape(state.members[index][key])}" placeholder="${placeholder}" maxlength="${key === "budget" ? 24 : 160}" ${key === "budget" ? 'inputmode="numeric"' : ""} ${errorAttrs(id, error)}>
    ${fieldError(id, error)}</div>`;
}

function renderMembers() {
  const rows = state.members.map((member, index) => `
    <fieldset class="member">
      <legend>Người ${index + 1}</legend>
      <div class="member-grid">
        ${memberField(index, "name", "Tên")}
        ${memberField(index, "budget", "Ngân sách gồm ship", "70.000đ")}
        ${memberField(index, "avoid", "Dị ứng hoặc điều kiêng", "Ví dụ dị ứng đậu phộng, cay")}
        ${memberField(index, "wants", "Món muốn ăn", "Ví dụ cơm gà")}
      </div>
      <div class="member-actions">
        <div class="check-row">
          <label class="check-label"><input type="checkbox" data-member="${index}" data-field="vegetarian" ${member.vegetarian ? "checked" : ""}> Ăn chay</label>
          <label class="check-label"><input type="checkbox" data-member="${index}" data-field="blind" ${member.blind ? "checked" : ""}> Ăn gì cũng được</label>
        </div>
        ${state.members.length > 1 ? textButton("Xóa người", "remove", `data-index="${index}" aria-label="Xóa người ${index + 1}"`) : ""}
      </div>
    </fieldset>`).join("");
  return `<form data-form="members" novalidate>
    ${state.text.trim() ? `<details class="source-draft"><summary>Xem tin nhắn gốc</summary><p>${escape(state.text)}</p></details>` : ""}
    <div class="members">${rows}</div>
    ${textButton("+ Thêm người", "add")}
    <div class="actions">${button("Quay lại", "back")}<button class="button primary" type="submit">Xác nhận và tìm quán</button></div>
  </form>`;
}

function renderRestaurants() {
  const rows = state.restaurants.map(restaurant => {
    const selected = state.restaurant?.restaurant_id === restaurant.restaurant_id;
    return `<article class="restaurant ${selected ? "selected" : ""}">
      <div class="restaurant-head"><h3>${escape(restaurant.name)}</h3><span class="money">${money(restaurant.ship_per_person_vnd)}/người</span></div>
      <p class="helper">${escape(restaurant.style)}</p>
      <div class="restaurant-foot"><span class="${selected ? "status-tag" : "helper"}">${selected ? "Đã chọn" : "Có món phù hợp cho từng người"}</span>
        ${button(selected ? "Xem lại giỏ" : "Chọn quán này", "choose", "secondary", `data-id="${escape(restaurant.restaurant_id)}" aria-label="${selected ? "Xem lại giỏ" : "Chọn quán này"}: ${escape(restaurant.name)}"`)}</div>
    </article>`;
  }).join("");
  return `<div class="cart-heading"><span class="status-tag">Menu mẫu</span></div>
    ${rows ? `<div class="restaurant-list">${rows}</div>` : alert(
      membersForCheck().some(member => member.allergies.length)
        ? "Chưa tìm được quán phù hợp. Với món thiếu thông tin dị ứng, cần xác nhận thành phần trước khi chọn."
        : "Chưa có quán nào đáp ứng đủ điều kiện và ngân sách của cả nhóm. Quay lại kiểm tra thông tin từng người."
    )}
    <div class="actions">${button("Quay lại xác nhận", "back")}</div>`;
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
          ${others.map(dish => `<option value="${escape(dish.id)}">${escape(dish.name)} · ${money(dish.price + item.ship_share_vnd)}</option>`).join("")}
          </select>
          <div class="swap-actions"><button class="button secondary" type="submit">Kiểm và đổi món</button>${textButton("Hủy đổi", "cancel")}</div>
        </form>`;
      } else if (state.changed.has(index)) {
        controls = '<p class="helper">Đã dùng lượt đổi món</p>';
      } else if (others.length) {
        controls = textButton("Đổi món", "swap", `data-index="${index}" aria-label="Đổi món cho ${escape(item.member_name)}"`);
      } else {
        controls = '<p class="helper">Chưa có món thay thế phù hợp</p>';
      }
    }
    return `<article class="cart-row">
      <div class="cart-item"><div class="cart-head"><h3>${escape(item.member_name)}</h3>${item.is_blind_bag ? '<span class="status-tag">Túi mù</span>' : ""}</div>
      <p class="dish">${escape(item.ten_mon)}</p></div>
      <div class="cart-cost"><span class="money">${money(item.price_vnd)} + ${money(item.ship_share_vnd)} ship</span><strong class="money">${money(item.total_member_vnd)}</strong></div>
      ${controls ? `<div class="cart-controls ${state.swap === index ? "expanded" : ""}">${controls}</div>` : ""}
    </article>`;
  }).join("");
  return `<div class="cart-heading"><h3>${escape(state.cart.restaurant_name)}</h3><span class="status-tag success">Giỏ đã kiểm</span></div>
    ${state.finalized ? alert("Đã chốt giỏ. Sao chép danh sách để tự đặt trên ứng dụng giao đồ ăn.", "success") : ""}
    ${rows}
    ${state.status ? alert(state.status, "success") : ""}
    <div class="actions">
      ${state.finalized ? textButton("Tạo đơn mới", "restart") : textButton("Đổi quán", "back")}
      ${button(state.finalized ? "Sao chép danh sách" : "Sao chép tin nhắn nháp", "copy")}
      ${state.finalized ? "" : button("Chốt giỏ", "finalize", "primary")}
    </div>
    ${state.fallback ? `<div class="field"><label for="copy-fallback">Chọn và sao chép danh sách</label><textarea id="copy-fallback" class="control copy-fallback" readonly>${escape(state.fallback)}</textarea></div>` : ""}`;
}

function renderSummary() {
  const rows = [["Số người", state.members.length ? state.members.length + " người" : "Chưa nhập"]];
  rows.push(["Quán đã chọn", state.restaurant?.name || "Chưa chọn"]);
  if (state.cart) {
    rows.push(["Tiền món", money(state.cart.total_food_vnd)], ["Phí ship", money(state.cart.shipping_fee_vnd)], ["Tổng đơn", money(state.cart.total_order_vnd)]);
  }
  const rounded = state.cart && state.cart.items.reduce((total, item) => total + item.total_member_vnd, 0) > state.cart.total_order_vnd;
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
  content.innerHTML = (state.notice ? alert(state.notice, "error") : "") +
    (state.busy ? alert(state.busy) : "") +
    [renderInput, renderMembers, renderRestaurants, renderCart][state.step]();
  content.setAttribute("aria-busy", String(Boolean(state.busy)));
  if (state.busy) content.querySelectorAll("button, input, select, textarea").forEach(control => { control.disabled = true; });
  renderSummary();
}

function readInput() {
  state.errors = {};
  if (!state.text.trim()) state.errors.text = "Dán tin nhắn nhóm hoặc chọn Nhập thủ công.";
  if (state.budget.trim() && !inputMoney(state.budget)) state.errors.budget = "Nhập số tiền, ví dụ 70.000đ.";
  if (Object.keys(state.errors).length) {
    render();
    content.querySelector("[aria-invalid]")?.focus();
    return;
  }
  const snapshot = JSON.stringify([state.text, state.budget]);
  if (state.parsed !== snapshot) {
    state.members = state.text.split(/\r?\n/).filter(line => line.trim()).map(line => readLine(line, state.budget));
    state.parsed = snapshot;
    resetCart();
  }
  navigate(1);
}

async function findRestaurants() {
  state.errors = {};
  const names = state.members.map(member => normalize(member.name.trim()));
  state.members.forEach((member, index) => {
    if (!member.name.trim()) state.errors[`member-${index}-name`] = "Nhập tên để phân biệt suất của từng người.";
    else if (names.indexOf(names[index]) !== index) state.errors[`member-${index}-name`] = "Tên bị trùng. Thêm họ hoặc biệt danh.";
    if (!inputMoney(member.budget)) state.errors[`member-${index}-budget`] = "Nhập ngân sách đã gồm phí ship.";
  });
  if (Object.keys(state.errors).length) {
    render();
    content.querySelector("[aria-invalid]")?.focus();
    return;
  }
  await pending("Đang tìm quán phù hợp…", async () => {
    const result = await request("restaurants");
    resetCart();
    state.restaurants = result.restaurants;
    navigate(2);
    title.focus();
  });
}

async function chooseRestaurant(id) {
  if (state.restaurant?.restaurant_id === id && state.cart) {
    navigate(3);
    return;
  }
  await pending("Đang dựng và kiểm giỏ…", async () => {
    const result = await request("options", { restaurant: id });
    if (result.options.some(dishes => !dishes.length)) throw new Error("Quán này chưa có món phù hợp cho tất cả mọi người.");
    const selections = result.options.map((dishes, index) => {
      const member = state.members[index];
      const preference = normalize(member.wants.trim());
      const recent = state.recentDishes.get(normalize(member.name.trim()));
      const alternatives = dishes.filter(dish => dish.id !== recent);
      const candidates = alternatives.length ? alternatives : dishes;
      const preferred = !member.blind && preference && candidates.find(dish => normalize(dish.name).includes(preference));
      return { member_name: member.name.trim(), dish_id: (preferred || candidates[0]).id, is_blind_bag: member.blind };
    });
    const cart = await request("check", { restaurant: id, selections });
    if (!cart.ok) throw new Error(cart.errors.join(" "));
    resetCart();
    state.restaurant = state.restaurants.find(restaurant => restaurant.restaurant_id === id);
    state.options = result.options;
    state.selections = selections;
    state.cart = cart;
    navigate(3);
  });
}

async function replaceDish(index, id) {
  if (state.changed.has(index)) return;
  const selections = state.selections.map((selection, choice) => choice === index ? { ...selection, dish_id: id } : selection);
  await pending("Đang kiểm món thay thế…", async () => {
    const cart = await request("check", { restaurant: state.restaurant.restaurant_id, selections });
    if (!cart.ok) throw new Error(cart.errors.join(" "));
    state.cart = cart;
    state.selections = selections;
    state.changed.add(index);
    state.swap = null;
    announcement.textContent = "Đã đổi món cho " + selections[index].member_name + ".";
  });
}

async function finalizeCart() {
  await pending("Đang kiểm lại toàn bộ giỏ…", async () => {
    const cart = await request("check", { restaurant: state.restaurant.restaurant_id, selections: state.selections });
    if (!cart.ok) {
      state.cart = null;
      throw new Error(cart.errors.join(" "));
    }
    state.cart = cart;
    state.finalized = true;
    for (const item of cart.items) state.recentDishes.set(normalize(item.member_name), item.dish_id);
    announcement.textContent = "Đã chốt giỏ.";
  });
}

async function copyCart() {
  const lines = [
    `${state.finalized ? "Danh sách chốt" : "Giỏ nháp"} · ${state.cart.restaurant_name}`,
    ...state.cart.items.map(item => `${item.member_name}: ${item.ten_mon} · ${money(item.total_member_vnd)} gồm ship`),
    `Tổng đơn: ${money(state.cart.total_order_vnd)}`,
  ];
  const text = lines.join("\n");
  try {
    await navigator.clipboard.writeText(text);
    state.status = "Đã sao chép danh sách.";
    state.fallback = "";
    render();
    content.querySelector('[data-action="copy"]')?.focus();
  } catch {
    state.fallback = text;
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

content.addEventListener("input", event => {
  const field = event.target;
  if (field.dataset.member !== undefined) {
    state.members[Number(field.dataset.member)][field.dataset.field] = field.type === "checkbox" ? field.checked : field.value;
  } else if (field.name === "text" || field.name === "budget") {
    state[field.name] = field.value;
  }
});

content.addEventListener("submit", async event => {
  event.preventDefault();
  if (state.busy) return;
  const form = event.target;
  switch (form.dataset.form) {
    case "read": readInput(); break;
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
    case "manual":
      if (!state.members.length) state.members.push({ ...emptyMember(), budget: state.budget });
      navigate(1);
      break;
    case "back":
      navigate(state.step - 1);
      break;
    case "add":
      state.members.push({ ...emptyMember(), budget: state.budget });
      render();
      content.querySelector(`#member-${state.members.length - 1}-name`).focus();
      break;
    case "remove":
      state.members.splice(index, 1);
      state.errors = {};
      render();
      content.querySelector(`#member-${Math.min(index, state.members.length - 1)}-name`).focus();
      break;
    case "choose": await chooseRestaurant(target.dataset.id); break;
    case "swap":
      state.swap = index;
      render();
      content.querySelector("#replacement").focus();
      break;
    case "cancel":
      const swapIndex = state.swap;
      state.swap = null;
      render();
      content.querySelector(`[data-action="swap"][data-index="${swapIndex}"]`)?.focus();
      break;
    case "copy": await copyCart(); break;
    case "finalize": await finalizeCart(); break;
    case "restart":
      resetCart();
      state.text = "";
      state.budget = "";
      state.parsed = "";
      state.members = [];
      state.restaurants = [];
      navigate(0);
      break;
  }
});

render();
