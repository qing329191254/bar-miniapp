<script setup lang="ts">
defineProps<{ modelValue: string; max?: string }>();
const emit = defineEmits<{ "update:modelValue": [string]; change: [] }>();

function onInput(e: Event) {
  emit("update:modelValue", (e.target as HTMLInputElement).value);
  emit("change");
}
function openDatePicker(e: Event) {
  const el = e.currentTarget as HTMLInputElement;
  try {
    el.showPicker?.();
  } catch {
    /* unsupported */
  }
}
</script>

<template>
  <label class="date-inp">
    <input
      type="date"
      class="inp date-inp-field"
      :class="{ 'is-empty': !modelValue }"
      :value="modelValue"
      :max="max"
      @input="onInput"
      @change="emit('change')"
      @click="openDatePicker"
    />
    <span v-if="!modelValue" class="date-inp-ph">年 / 月 / 日</span>
  </label>
</template>

<style scoped>
.date-inp {
  position: relative;
  display: inline-block;
}
.date-inp-field {
  width: auto;
  min-width: 150px;
  max-width: 150px;
  margin: 0;
}
.date-inp-ph {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--ink3);
  font-size: 13px;
  pointer-events: none;
}
.date-inp-field.is-empty:not(:focus)::-webkit-datetime-edit {
  opacity: 0;
}
</style>
