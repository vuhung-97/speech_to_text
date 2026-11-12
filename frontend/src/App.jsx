import DictationPage from "./pages/DictationPage";
import Toast from "./components/Toast";
import { AppProvider } from "./context/AppContext";

export default function App() {
  return (
    <AppProvider>
      <DictationPage />
      <Toast />
    </AppProvider>
  );
}
