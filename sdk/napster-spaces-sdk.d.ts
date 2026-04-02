export declare interface FeatureConfig {
    backgroundRemoval: {
        enabled: boolean;
    };
    waveform: {
        enabled: boolean;
        color?: string;
    };
    inactiveTimeout: {
        enabled: boolean;
        duration?: number;
    };
    disclaimer: {
        enabled: boolean;
        text?: string;
    };
}

declare interface NapsterSpacesSDK {
    init: (config: SpacesConfig) => Promise<SpacesInstance>;
    version: string;
}

export declare const napsterSpacesSDK: Spaces;

declare type Position = 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left' | 'center';

declare class Spaces implements NapsterSpacesSDK {
    private static instance;
    readonly version: string;
    private container;
    private root;
    private config;
    private constructor();
    static getInstance(): Spaces;
    init(config: SpacesConfig): Promise<SpacesInstance>;
}

export declare interface SpacesConfig {
    experienceId: string;
    instructions?: string;
    functions?: string | string[];
    functionsLibraryId?: string;
    position?: Position;
    className?: string;
    style?: React.CSSProperties;
    features?: FeatureConfig;
    startWithoutPreview?: boolean;
    container?: HTMLElement | string;
    onReady?: () => void;
    onError?: (error: Error) => void;
    onData?: (data: any) => void;
    onAvatarReady?: () => void;
    onApiReady?: (api: SpacesPublicApi) => void;
}

export declare interface SpacesInstance {
    show: () => void;
    hide: () => void;
    destroy: () => void;
    updateStyles: (styles: StyleConfig) => void;
    enableFeature: (feature: keyof FeatureConfig) => void;
    disableFeature: (feature: keyof FeatureConfig) => void;
    updateFeatureConfig: (feature: keyof FeatureConfig, config: Partial<NonNullable<FeatureConfig>[keyof FeatureConfig]>) => void;
    sendQuestion: (text: string) => void;
    sendMessage: (command: SpacesSendMessageCommand) => void;
    sendFunctionOutput: (callId: string, output: unknown) => void;
    stopTalk: () => void;
    stopSession: () => void;
    startSession: () => void;
    setPreviewHidden: (hidden?: boolean) => void;
    setAvatarHidden: (hidden?: boolean) => void;
    setUserMuted: (muted?: boolean) => void;
    setAvatarMuted: (muted?: boolean) => void;
}

export declare interface SpacesPublicApi {
    startSession: () => void;
    stopSession: () => void;
    sendQuestion: (text: string) => void;
    sendMessage: (command: SpacesSendMessageCommand) => void;
    sendFunctionOutput: (callId: string, output: unknown) => void;
    stopTalk: () => void;
    setPreviewHidden: (hidden?: boolean) => void;
    setAvatarHidden: (hidden?: boolean) => void;
    setUserMuted: (muted?: boolean) => void;
    setAvatarMuted: (muted?: boolean) => void;
}

export declare interface SpacesSendMessageCommand {
    text: string;
    /**
     * When true, forces an avatar response after the message.
     */
    triggerResponse?: boolean;
    /**
     * When true (default), queues the message to respect the current flow.
     */
    delay?: boolean;
    /**
     * Optional role field forwarded to the data channel payload.
     */
    role?: string;
}

export declare interface StyleConfig {
    containerClassName?: string;
    containerStyle?: React.CSSProperties;
    embedClassName?: string;
    embedStyle?: React.CSSProperties;
    cssVariables?: {
        primaryColor?: string;
        secondaryColor?: string;
        backgroundColor?: string;
        textColor?: string;
        width?: string;
        height?: string;
        borderRadius?: string;
        [key: string]: string | undefined;
    };
}

export { }


declare global {
    interface Window {
        napsterSpacesSDK: NapsterSpacesSDK;
    }
}

declare global {
    interface HTMLCanvasElement {
        getContext(contextId: 'webgl' | 'experimental-webgl', contextAttributes?: WebGLContextAttributes): WebGLRenderingContext | null;
        getContext(contextId: '2d', contextAttributes?: CanvasRenderingContext2DSettings): CanvasRenderingContext2D | null;
        getContext(contextId: string, contextAttributes?: Record<string, unknown>): RenderingContext | null;
    }
}

