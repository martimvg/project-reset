# Setting up the website (about 30 minutes, no coding)

The code is ready. You only need to create three free accounts and copy a few values between them.
Keep the secret keys private: paste them only into the places named below, never into chats, emails or documents.

What each service does, in one line:
- **Supabase**: the database (stores roles, users, applications) and the sign-in system.
- **Vercel**: puts the website on the internet and rebuilds it every time the code on GitHub changes.
- **GitHub**: already set up. It holds the code and runs the robot.

## 1. Create the database (Supabase), about 10 minutes

1. Go to supabase.com and choose **Start your project**. Sign in with your GitHub account.
2. Choose **New project**:
   - Name: `applicant-desk`.
   - Database password: let it generate one, and save it in your password manager.
   - Region: **London (eu-west-2)**.
   - Plan: Free.
3. Wait about 2 minutes while it is created.
4. In the left menu open **SQL Editor**, then **New query**.
5. On GitHub, open the file `supabase/schema.sql` in this project, copy all of it, paste it into the editor, and press **Run**. It should say "Success".
6. Open **Project Settings → API** (in some versions: **Project Settings → Data API** and **API Keys**). You will need three values:
   - **Project URL** (looks like `https://abcd1234.supabase.co`)
   - **anon / public key** (safe to use in the website)
   - **service_role / secret key** (secret: only for GitHub, step 2)

## 2. Let the robot fill the database (GitHub), about 5 minutes

1. On GitHub, open the `project-reset` repository, then **Settings → Secrets and variables → Actions**.
2. Choose **New repository secret** twice:
   - Name `SUPABASE_URL`, value: the Project URL.
   - Name `SUPABASE_SERVICE_KEY`, value: the service_role / secret key.
3. Open the **Actions** tab, then **Check for new roles**, then **Run workflow**. After about 10 minutes, Supabase's **Table Editor → openings** will list about 220 roles.

## 3. Put the website online (Vercel), about 10 minutes

1. Go to vercel.com and choose **Sign up**. Use **Continue with GitHub** and the free Hobby plan.
2. Choose **Add New… → Project**, find `project-reset`, and choose **Import**.
3. Set **Root Directory** to `web`.
4. Open **Environment Variables** and add:
   - `NEXT_PUBLIC_SUPABASE_URL`: the Project URL.
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: the anon / public key.
5. Press **Deploy**. After about 2 minutes you get an address like `applicant-desk-xxxx.vercel.app`. That is your website.

## 4. Turn on sign-in, about 3 minutes

1. In Supabase open **Authentication → URL Configuration**.
2. Set **Site URL** to your Vercel address.
3. Under Redirect URLs, add the same address followed by `/**`.
4. Email sign-in links now work. Google sign-in can be switched on later under **Authentication → Providers → Google**.

## 5. Make yourself the admin, 1 minute

1. Sign in on your website once.
2. In Supabase open **Table Editor → profiles**, find your row, set `is_admin` to `true`, and save.
3. You can now use **Add a role** on the Tracker.

## 6. Later: switch on the AI features

1. Create an account at console.anthropic.com, add a payment method, and create an API key.
2. In Vercel open **Project → Settings → Environment Variables** and add `ANTHROPIC_API_KEY`.
3. Redeploy the project.

Each student gets 30 AI requests a month. Change this with the `AI_MONTHLY_LIMIT` setting.
Cost is roughly $0.02–0.05 per CV or letter.

## Costs

- **While building**: £0. Supabase Free and Vercel Hobby cost nothing.
- **At launch**: Vercel Pro is $20 a month (needed for commercial use), Supabase Pro is $25 a month, and the domain is about £10–15 a year.
