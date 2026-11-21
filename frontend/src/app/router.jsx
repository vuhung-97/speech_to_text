// Client router: one URL per screen so deep links, refresh and back/forward all
// work. `/sessions/:id` reopens a persisted conversation.

import { createBrowserRouter } from "react-router-dom";

import DictationPage from "../features/dictation";
import FaqAdminPage from "../features/faq";
import QaPage from "../features/qa";
import SessionListPage from "../features/sessions";
import NotFoundPage from "../pages/NotFoundPage";
import SettingsPage from "../pages/SettingsPage";

export const router = createBrowserRouter([
  { path: "/", element: <QaPage /> },
  { path: "/sessions", element: <SessionListPage /> },
  { path: "/sessions/:id", element: <QaPage /> },
  { path: "/faq", element: <FaqAdminPage /> },
  { path: "/dictation", element: <DictationPage /> },
  { path: "/settings", element: <SettingsPage /> },
  { path: "*", element: <NotFoundPage /> },
]);
