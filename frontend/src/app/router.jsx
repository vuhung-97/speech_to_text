// Client router: one URL per screen so deep links, refresh and back/forward all
// work. `/sessions/:id` reopens a persisted conversation.

import { createBrowserRouter } from "react-router-dom";

import FaqAdminPage from "../features/faq";
import QaPage from "../features/qa";
import SessionListPage from "../features/sessions";
import NotFoundPage from "../pages/NotFoundPage";

export const router = createBrowserRouter([
  { path: "/", element: <QaPage /> },
  { path: "/sessions", element: <SessionListPage /> },
  { path: "/sessions/:id", element: <QaPage /> },
  { path: "/faq", element: <FaqAdminPage /> },
  { path: "*", element: <NotFoundPage /> },
]);
