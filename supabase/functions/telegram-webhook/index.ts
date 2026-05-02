const TELEGRAM_API = "https://api.telegram.org";

type TelegramUpdate = {
  message?: {
    text?: string;
    chat?: { id?: number | string };
  };
};

function env(name: string): string {
  const value = Deno.env.get(name);
  if (!value) throw new Error(`Missing required env var: ${name}`);
  return value;
}

async function sendTelegram(chatId: string, text: string) {
  const token = env("TELEGRAM_BOT_TOKEN");
  await fetch(`${TELEGRAM_API}/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      disable_web_page_preview: true,
    }),
  });
}

function parseCommand(text = "") {
  const [command = "", password = ""] = text.trim().split(/\s+/, 2);
  return { command: command.toLowerCase(), password };
}

async function triggerWorkflow(command: string) {
  const owner = env("GITHUB_OWNER");
  const repo = env("GITHUB_REPO");
  const workflow = Deno.env.get("GITHUB_WORKFLOW_FILE") || "agent-run.yml";
  const token = env("GITHUB_PAT");
  const ref = Deno.env.get("GITHUB_REF") || "main";

  const res = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
        "User-Agent": "job-search-os-telegram-webhook",
      },
      body: JSON.stringify({ ref, inputs: { command } }),
    },
  );

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GitHub workflow trigger failed: ${res.status} ${body}`);
  }
}

async function cancelWorkflow() {
  const owner = env("GITHUB_OWNER");
  const repo = env("GITHUB_REPO");
  const workflow = Deno.env.get("GITHUB_WORKFLOW_FILE") || "agent-run.yml";
  const token = env("GITHUB_PAT");
  const headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": `Bearer ${token}`,
    "User-Agent": "job-search-os-telegram-webhook",
  };
  const runsRes = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/runs?status=in_progress&per_page=5`,
    { headers },
  );
  if (!runsRes.ok) throw new Error(`GitHub run lookup failed: ${runsRes.status}`);
  const runs = (await runsRes.json()).workflow_runs || [];
  for (const run of runs) {
    await fetch(`https://api.github.com/repos/${owner}/${repo}/actions/runs/${run.id}/cancel`, {
      method: "POST",
      headers,
    });
  }
  return runs.length;
}

async function fetchJobs(path: string) {
  const url = `${env("SUPABASE_URL")}/rest/v1/${path}`;
  const key = env("SUPABASE_SERVICE_ROLE_KEY");
  const res = await fetch(url, {
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
    },
  });
  if (!res.ok) throw new Error(`Supabase query failed: ${res.status}`);
  return await res.json();
}

async function handleStatus(chatId: string) {
  const rows = await fetchJobs("jobs?select=status");
  const stats: Record<string, number> = {};
  for (const row of rows) stats[row.status || "unknown"] = (stats[row.status || "unknown"] || 0) + 1;
  const lines = Object.entries(stats).map(([key, value]) => `- ${key}: ${value}`);
  await sendTelegram(chatId, `*Job Search OS status*\n${lines.join("\n") || "No jobs yet."}`);
}

async function handleJobs(chatId: string) {
  const rows = await fetchJobs("jobs?select=title,company,score,url,status&status=in.(new,applied)&order=score.desc&limit=5");
  if (!rows.length) {
    await sendTelegram(chatId, "No saved jobs yet.");
    return;
  }
  const lines = rows.map((j: any, i: number) =>
    `${i + 1}. *${j.title}* @ ${j.company}\nScore: ${j.score ?? "n/a"} | ${j.status}\n${j.url}`
  );
  await sendTelegram(chatId, `*Top jobs*\n\n${lines.join("\n\n")}`);
}

Deno.serve(async (req) => {
  try {
    const update = await req.json() as TelegramUpdate;
    const chatId = String(update.message?.chat?.id || "");
    const text = update.message?.text || "";
    const allowedChatId = env("TELEGRAM_CHAT_ID");
    const commandPassword = env("COMMAND_PASSWORD");

    if (chatId !== allowedChatId) return new Response("ignored", { status: 200 });

    const { command, password } = parseCommand(text);
    if (password !== commandPassword) {
      await sendTelegram(chatId, "Unauthorized command.");
      return new Response("ok", { status: 200 });
    }

    if (command === "/run") {
      await triggerWorkflow("run");
      await sendTelegram(chatId, "Starting Job Search OS cloud run.");
    } else if (command === "/discover") {
      await triggerWorkflow("discover");
      await sendTelegram(chatId, "Starting discovery-only cloud run.");
    } else if (command === "/apply") {
      await triggerWorkflow("apply");
      await sendTelegram(chatId, "Starting application-writing cloud run.");
    } else if (command === "/stop") {
      const count = await cancelWorkflow();
      await sendTelegram(chatId, count ? `Requested cancellation for ${count} active run(s).` : "No active cloud runs found.");
    } else if (command === "/status") {
      await handleStatus(chatId);
    } else if (command === "/jobs") {
      await handleJobs(chatId);
    } else if (command === "/help") {
      await sendTelegram(chatId, "Commands:\n/run <password>\n/discover <password>\n/apply <password>\n/stop <password>\n/status <password>\n/jobs <password>\n/help <password>");
    } else {
      await sendTelegram(chatId, "Unknown command. Try /help <password>.");
    }

    return new Response("ok", { status: 200 });
  } catch (error) {
    console.error(error);
    return new Response("error", { status: 500 });
  }
});
