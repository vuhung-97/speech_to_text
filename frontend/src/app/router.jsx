// Client router: one URL per screen so deep links, refresh and back/forward all
// work. Screens that do not exist yet answer with an honest placeholder.

import { createBrowserRouter } from "react-router-dom";

import DictationPage from "../pages/DictationPage";
import FaqPage from "../pages/FaqPage";
import NotFoundPage from "../pages/NotFoundPage";
import SessionsPage from "../pages/SessionsPage";
import SettingsPage from "../pages/SettingsPage";

export const router = createBrowserRouter([
  { path: "/", element: <DictationPage /> },
  { path: "/sessions", element: <SessionsPage /> },
  { path: "/faq", element: <FaqPage /> },
  { path: "/settings", element: <SettingsPage /> },
  { path: "*", element: <NotFoundPage /> },
]);
