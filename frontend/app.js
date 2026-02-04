const qs = (id) => document.getElementById(id);

const state = {
  baseUrl: "http://127.0.0.1:5000",
  token: "",
  userType: "",
};

const toast = (msg) => {
  const el = qs("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2000);
};

const apiFetch = async (path, options = {}) => {
  const url = `${state.baseUrl}${path}`;
  const headers = options.headers || {};
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  const res = await fetch(url, { ...options, headers });
  const data = await res.json();
  if (!res.ok || data.success === false) {
    throw new Error(data.message || "请求失败");
  }
  return data;
};

qs("saveBase").onclick = () => {
  const val = qs("apiBase").value.trim();
  if (val) {
    state.baseUrl = val;
    toast("已更新 API Base");
  }
};

qs("regBtn").onclick = async () => {
  try {
    const payload = {
      username: qs("regUsername").value.trim(),
      password: qs("regPassword").value.trim(),
      user_type: qs("regUserType").value,
      real_name: qs("regRealName").value.trim(),
      school_company: qs("regSchoolCompany").value.trim(),
      skill_tags: qs("regSkillTags").value.trim(),
      contact: qs("regContact").value.trim(),
    };
    const data = await apiFetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    toast(data.message || "注册成功");
  } catch (err) {
    toast(err.message);
  }
};

qs("loginBtn").onclick = async () => {
  try {
    const payload = {
      username: qs("loginUsername").value.trim(),
      password: qs("loginPassword").value.trim(),
    };
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.token = data.token;
    state.userType = data.user_type;
    qs("tokenPreview").textContent = data.token;
    qs("userTypePreview").textContent = data.user_type;
    toast("登录成功");
  } catch (err) {
    toast(err.message);
  }
};

qs("loadProjects").onclick = async () => {
  try {
    const q = qs("searchKeyword").value.trim();
    const query = q ? `?q=${encodeURIComponent(q)}` : "";
    const data = await apiFetch(`/api/projects${query}`);
    const list = data.projects || [];
    qs("projectList").innerHTML = list
      .map(
        (p) => `
        <div class="item">
          <div><b>${p.project_name}</b> <span>(${p.project_status})</span></div>
          <div>${p.description || ""}</div>
          <div>公司：${p.company || "-"}</div>
        </div>
      `
      )
      .join("");
  } catch (err) {
    toast(err.message);
  }
};

qs("loadProjectDetail").onclick = async () => {
  try {
    const id = qs("projectId").value.trim();
    const data = await apiFetch(`/api/projects/${id}`);
    const project = data.project;
    const roles = data.roles || [];
    qs("projectDetail").innerHTML = `
      <div class="item">
        <div><b>${project.project_name}</b></div>
        <div>${project.description || ""}</div>
        <div>状态：${project.project_status}</div>
        <div>发布方：${project.publisher_name || ""}</div>
      </div>
      ${roles
        .map(
          (r) => `
          <div class="item">
            <div><b>${r.role_name}</b> (${r.role_status})</div>
            <div>${r.task_desc || ""}</div>
            <div>技能：${r.skill_require || ""}</div>
            <div>名额：${r.join_num}/${r.limit_num}</div>
          </div>
        `
        )
        .join("")}
    `;
  } catch (err) {
    toast(err.message);
  }
};

qs("createProject").onclick = async () => {
  try {
    const payload = {
      project_name: qs("projName").value.trim(),
      description: qs("projDesc").value.trim(),
      company: qs("projCompany").value.trim(),
      project_status: qs("projStatus").value.trim() || "招募中",
      deadline: qs("projDeadline").value.trim() || null,
    };
    const data = await apiFetch("/api/enterprise/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    toast(`项目创建成功：${data.project_id}`);
  } catch (err) {
    toast(err.message);
  }
};

qs("createRole").onclick = async () => {
  try {
    const projectId = qs("roleProjectId").value.trim();
    const payload = {
      role_name: qs("roleName").value.trim(),
      task_desc: qs("roleDesc").value.trim(),
      skill_require: qs("roleSkills").value.trim(),
      limit_num: Number(qs("roleLimit").value.trim() || 1),
      role_status: qs("roleStatus").value.trim() || "招募中",
      task_deadline: qs("roleDeadline").value.trim() || null,
    };
    const data = await apiFetch(`/api/enterprise/projects/${projectId}/roles`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    toast(`角色创建成功：${data.role_id}`);
  } catch (err) {
    toast(err.message);
  }
};

qs("applyRole").onclick = async () => {
  try {
    const roleId = qs("applyRoleId").value.trim();
    const payload = { motivation: qs("applyMotivation").value.trim() };
    const data = await apiFetch(`/api/roles/${roleId}/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    toast(`申请成功：${data.application_id}`);
  } catch (err) {
    toast(err.message);
  }
};

qs("loadMyApps").onclick = async () => {
  try {
    const data = await apiFetch("/api/student/applications");
    const list = data.applications || [];
    qs("myApps").innerHTML = list
      .map(
        (a) => `
        <div class="item">
          <div><b>${a.project_name}</b> - ${a.role_name}</div>
          <div>状态：${a.status}</div>
          <div>动机：${a.motivation || ""}</div>
        </div>
      `
      )
      .join("");
  } catch (err) {
    toast(err.message);
  }
};

qs("loadRoleApps").onclick = async () => {
  try {
    const roleId = qs("appsRoleId").value.trim();
    const data = await apiFetch(`/api/enterprise/roles/${roleId}/applications`);
    const list = data.applications || [];
    qs("roleApps").innerHTML = list
      .map(
        (a) => `
        <div class="item">
          <div><b>${a.student_name}</b> (${a.real_name || ""})</div>
          <div>状态：${a.status}</div>
          <div>动机：${a.motivation || ""}</div>
        </div>
      `
      )
      .join("");
  } catch (err) {
    toast(err.message);
  }
};

qs("reviewApp").onclick = async () => {
  try {
    const appId = qs("reviewAppId").value.trim();
    const payload = { decision: qs("reviewDecision").value };
    await apiFetch(`/api/enterprise/applications/${appId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    toast("审核完成");
  } catch (err) {
    toast(err.message);
  }
};
