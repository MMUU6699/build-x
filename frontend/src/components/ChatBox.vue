<template>
    <div class="pb-3 relative bg-[var(--background-gray-main)]">
        <!-- ç»“æž„ç…§æŠ„ manus.im ä¼šè¯ è¾“å…¥æ¡†ï¼šåœ†è§’å ¡ç‰‡ + åº•æ  + / é™„ä»¶ / éº¦ / å ‘é€  -->
        <div
            class="ai-glow-wrapper flex flex-col gap-2 rounded-[22px] transition-all relative pt-3 pb-2.5 max-h-[300px] shadow-[0px_12px_32px_0px_rgba(0,0,0,0.02)] border-transparent focus-within:border-transparent">
            <!-- Dedicated background layer to allow negative z-index pseudo-elements to glow behind it without disappearing -->
            <div class="absolute inset-0 bg-[var(--background-menu-white)] rounded-[22px] pointer-events-none" style="z-index: 0;"></div>
            
            <div class="relative z-10 w-full flex flex-col gap-2">
                <ChatBoxFiles ref="chatBoxFileListRef" :attachments="attachments"
                    @update:attachments="emit('update:attachments', $event)" />
                <div class="overflow-auto ps-4 pe-4 min-h-[46px] w-full text-[15px] leading-[24px]">
                    <textarea
                        class="flex rounded-md border-input focus-visible:outline-none focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 overflow-hidden flex-1 bg-transparent p-0 pt-[1px] border-0 focus-visible:ring-0 focus-visible:ring-offset-0 w-full placeholder:text-[var(--text-disable)] text-[15px] leading-[24px] shadow-none resize-none min-h-[40px]"
                        :rows="rows" :value="modelValue"
                        @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
                        @compositionstart="isComposing = true" @compositionend="isComposing = false"
                        @keydown.enter.exact="handleEnterKeydown" :placeholder="placeholderText"
                        :style="{ height: '46px' }"></textarea>
                </div>
                <footer class="flex gap-1.5 px-3 items-center">
                    <div class="relative" ref="plusMenuRef">
                        <button type="button" @click="showPlusMenu = !showPlusMenu"
                            class="rounded-full inline-flex items-center justify-center clickable cursor-pointer text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-white-light)] w-8 h-8 p-0 shrink-0"
                            :title="t('Add files and more')"
                            aria-expanded="false" aria-haspopup="dialog">
                            <Plus :size="18" />
                        </button>
                        <div v-if="showPlusMenu"
                            class="absolute bottom-[calc(100%+8px)] start-0 z-50 min-w-[200px] rounded-[12px] border border-[var(--border-light)] bg-[var(--background-menu-white)] shadow-[0px_8px_32px_0px_var(--shadow-S)] py-1">
                            <button type="button"
                                class="flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--fill-tsp-white-main)]"
                                @click="handleAddLocalFiles">
                                <Paperclip :size="16" class="text-[var(--icon-tertiary)]" />
                                {{ t('Add local files') }}
                            </button>
                        </div>
                    </div>
                    <button type="button" @click="uploadFile"
                        class="rounded-full inline-flex items-center justify-center clickable cursor-pointer text-[var(--text-secondary)] hover:bg-[var(--fill-tsp-white-light)] w-8 h-8 p-0 shrink-0"
                        :title="t('Add local files')">
                        <Paperclip :size="18" />
                    </button>
                    <div class="flex gap-1.5 ms-auto items-center">
                        <button v-if="!isRunning || sendEnabled || hideStopButton"
                            class="inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors text-sm rounded-full p-0 w-8 h-8 min-w-0 hover:opacity-90"
                            :class="!sendEnabled ? 'cursor-not-allowed bg-[var(--fill-tsp-white-dark)] hover:opacity-100' : 'cursor-pointer bg-[var(--Button-primary-black)]'"
                            @click="handleSubmit">
                            <SendIcon :disabled="!sendEnabled" />
                        </button>
                        <button v-else-if="!hideStopButton" @click="handleStop"
                            class="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-colors bg-[var(--Button-primary-black)] text-[var(--text-onblack)] gap-[4px] hover:opacity-90 rounded-full p-0 w-8 h-8">
                            <div class="w-[10px] h-[10px] bg-[var(--icon-onblack)] rounded-[2px]">
                            </div>
                        </button>
                    </div>
                </footer>
            </div>
        </div>
    </div>
</template>    </div>
            </footer>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted } from 'vue';
import SendIcon from './icons/SendIcon.vue';
import { useI18n } from 'vue-i18n';
import ChatBoxFiles from './ChatBoxFiles.vue';
import { Paperclip, Plus } from 'lucide-vue-next';
import type { FileInfo } from '../api/file';

const { t } = useI18n();
const hasTextInput = ref(false);
const isComposing = ref(false);
const chatBoxFileListRef = ref();
const showPlusMenu = ref(false);
const plusMenuRef = ref<HTMLElement | null>(null);

const props = withDefaults(defineProps<{
    modelValue: string;
    rows: number;
    isRunning: boolean;
    attachments: FileInfo[];
    hideStopButton?: boolean;
    allowSendFilesOnly?: boolean;
    /** Build X session detail uses "Send message to Build X"; home keeps the task prompt. */
    placeholder?: string;
}>(), {
    placeholder: undefined,
});

const placeholderText = computed(() => props.placeholder || t('Give Build X a task to work on...'));

const sendEnabled = computed(() => {
    const hasFiles = (props.attachments?.length ?? 0) > 0;
    const allUploaded = chatBoxFileListRef.value?.isAllUploaded ?? true;
    if (props.allowSendFilesOnly) {
        return hasTextInput.value || (hasFiles && allUploaded);
    }
    return hasTextInput.value && (!hasFiles || allUploaded);
});

const emit = defineEmits<{
    (e: 'update:modelValue', value: string): void;
    (e: 'update:attachments', value: FileInfo[]): void;
    (e: 'submit'): void;
    (e: 'stop'): void;
}>();

watch(() => props.modelValue, (val) => {
    hasTextInput.value = !!val.trim();
}, { immediate: true });

const handleEnterKeydown = (e: KeyboardEvent) => {
    if (!isComposing.value && hasTextInput.value) {
        e.preventDefault();
        handleSubmit();
    }
};

const handleSubmit = () => {
    if (!sendEnabled.value) return;
    emit('submit');
};

const handleStop = () => {
    emit('stop');
};

const uploadFile = () => {
    chatBoxFileListRef.value?.uploadFile();
};

const handleAddLocalFiles = () => {
    showPlusMenu.value = false;
    uploadFile();
};

const onDocClick = (e: MouseEvent) => {
    if (showPlusMenu.value && plusMenuRef.value && !plusMenuRef.value.contains(e.target as Node)) {
        showPlusMenu.value = false;
    }
};

onMounted(() => document.addEventListener('mousedown', onDocClick));
onUnmounted(() => document.removeEventListener('mousedown', onDocClick));
</script>

<style scoped>
.ai-glow-wrapper {
  position: relative;
  z-index: 1;
}
.ai-glow-wrapper::before {
  content: "";
  position: absolute;
  inset: -3px;
  border-radius: 25px;
  background: linear-gradient(90deg, #00f0ff, #0055ff, #7000ff, #00f0ff);
  background-size: 300% 300%;
  animation: aiGlow 4s linear infinite;
  z-index: -2;
  filter: blur(8px);
  opacity: 0.5;
  transition: opacity 0.3s ease, filter 0.3s ease;
}
.ai-glow-wrapper::after {
  content: "";
  position: absolute;
  inset: -1px;
  border-radius: 23px;
  background: linear-gradient(90deg, #00f0ff, #0055ff, #7000ff, #00f0ff);
  background-size: 300% 300%;
  animation: aiGlow 4s linear infinite;
  z-index: -1;
}
.ai-glow-wrapper:focus-within::before {
  opacity: 0.8;
  filter: blur(12px);
}
@keyframes aiGlow {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
</style>
