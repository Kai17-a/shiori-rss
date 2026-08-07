import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";
import PrimeVue from "primevue/config";
import Aura from "@primeuix/themes/aura";

import Button from "primevue/button";
import Card from "primevue/card";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import MultiSelect from "primevue/multiselect";
import Select from "primevue/select";
import Textarea from "primevue/textarea";

const app = createApp(App);

app.use(PrimeVue, {
  theme: {
    preset: Aura,
  },
});
app.component("Button", Button);
app.component("Card", Card);
app.component("InputText", InputText);
app.component("Message", Message);
app.component("MultiSelect", MultiSelect);
app.component("Select", Select);
app.component("Textarea", Textarea);

app.mount("#app");
