import { TServiceParams } from "@digital-alchemy/core";
import { Dayjs } from "dayjs";

import {
  AddEntityOptions,
  BasicAddParams,
  CallbackData,
  SettableConfiguration,
} from "../../helpers/index.mts";

enum MediaType {
  MUSIC = "music",
  TVSHOW = "tvshow",
  MOVIE = "movie",
  VIDEO = "video",
  EPISODE = "episode",
  CHANNEL = "channel",
  PLAYLIST = "playlist",
  IMAGE = "image",
  URL = "url",
  GAME = "game",
  APP = "app",
}

enum MediaDeviceClass {
  TV = "tv",
  SPEAKER = "speaker",
  RECEIVER = "receiver",
}

type MediaPlayerEnqueue = "add" | "next" | "play" | "replace";

export type MediaPlayerConfiguration<
  DATA extends object,
  SOURCES extends string = string,
  SOUND_MODES extends string = string,
> = {
  /**
   * ID of the current running app.
   */
  app_id?: SettableConfiguration<string, DATA>;
  /**
   * Name of the current running app.
   */
  app_name?: SettableConfiguration<string, DATA>;
  /**
   * Type of media player.
   */
  device_class?: `${MediaDeviceClass}`;
  /**
   * A dynamic list of player entities which are currently grouped together for synchronous playback.
   * If the platform has a concept of defining a group leader, the leader should be the first element in that list.
   */
  group_members?: SettableConfiguration<string[], DATA>;
  /**
   * True if if volume is currently muted.
   */
  is_volume_muted?: SettableConfiguration<boolean, DATA>;
  /**
   * Album artist of current playing media, music track only.
   */
  media_album_artist?: SettableConfiguration<string, DATA>;
  /**
   * Album name of current playing media, music track only.
   */
  media_album_name?: SettableConfiguration<string, DATA>;
  /**
   * Album artist of current playing media, music track only.
   */
  media_artist?: SettableConfiguration<string, DATA>;
  /**
   * Channel currently playing.
   */
  media_channel?: SettableConfiguration<string, DATA>;
  /**
   * Content ID of current playing media.
   */
  media_content_id?: SettableConfiguration<string, DATA>;
  /**
   * Content type of current playing media.
   */
  media_content_type?: SettableConfiguration<`${MediaType}`, DATA>;
  /**
   * Duration of current playing media in seconds.
   */
  media_duration?: SettableConfiguration<number, DATA>;
  /**
   * Episode of current playing media, TV show only.
   */
  media_episode?: SettableConfiguration<string, DATA>;
  /**
   * Hash of media image, defaults to SHA256 of media_image_url if media_image_url is not None.
   */
  media_image_hash?: SettableConfiguration<string, DATA>;
  /**
   * True if property media_image_url is accessible outside of the home network.
   */
  media_image_remotely_accessible?: SettableConfiguration<boolean, DATA>;
  /**
   * Image URL of current playing media.
   */
  media_image_url?: SettableConfiguration<string, DATA>;
  /**
   * Title of Playlist currently playing.
   */
  media_playlist?: SettableConfiguration<string, DATA>;
  /**
   * Position of current playing media in seconds.
   */
  media_position?: SettableConfiguration<number, DATA>;
  /**
   * Timestamp of when _attr_media_position was last updated. The timestamp should be set by calling homeassistant.util.dt.utcnow().
   */
  media_position_updated_at?: SettableConfiguration<Dayjs, DATA>;
  /**
   * Season of current playing media, TV show only.
   */
  media_season?: SettableConfiguration<string, DATA>;
  /**
   * Title of series of current playing media, TV show only.
   */
  media_series_title?: SettableConfiguration<string, DATA>;
  /**
   * Title of current playing media.
   */
  media_title?: SettableConfiguration<string, DATA>;
  /**
   * Track number of current playing media, music track only.
   */
  media_track?: SettableConfiguration<string, DATA>;
  /**
   * Current repeat mode.
   */
  repeat?: SettableConfiguration<string, DATA>;
  /**
   * True if shuffle is enabled.
   */
  shuffle?: SettableConfiguration<boolean, DATA>;
  /**
   * The current sound mode of the media player.
   */
  sound_mode?: SettableConfiguration<SOUND_MODES, DATA>;
  /**
   * Dynamic list of available sound modes.
   */
  sound_mode_list?: SOUND_MODES[];
  /**
   * The currently selected input source for the media player.
   */
  source?: SettableConfiguration<SOURCES, DATA>;
  /**
   * The list of possible input sources for the media player. (This list should contain human readable names, suitable for frontend display).
   */
  source_list?: SOURCES[];

  supported_features?: number;
  /**
   * Volume level of the media player in the range (0..1).
   */
  volume_level?: SettableConfiguration<number, DATA>;
  /**
   * Volume step to use for the volume_up and volume_down services.
   */
  volume_step?: SettableConfiguration<string, DATA>;
};

export type MediaPlayerEvents = {
  select_sound_mode: { source: string };
  select_source: { source: string };
  play_media: {
    media_type: string;
    media_id: string;
    enqueue?: MediaPlayerEnqueue;
    announce?: boolean;
  };
};

export function VirtualMediaPlayer({ context, synapse }: TServiceParams) {
  const generate = synapse.generator.create<MediaPlayerConfiguration<object>, MediaPlayerEvents>({
    bus_events: ["select_sound_mode", "select_source", "play_media"],
    context,
    // @ts-expect-error its fine
    domain: "media_player",
    load_config_keys: [
      "app_id",
      "app_name",
      "device_class",
      "group_members",
      "is_volume_muted",
      "media_album_artist",
      "media_album_name",
      "media_artist",
      "media_channel",
      "media_content_id",
      "media_content_type",
      "media_duration",
      "media_episode",
      "media_image_hash",
      "media_image_remotely_accessible",
      "media_image_url",
      "media_playlist",
      "media_position",
      "media_position_updated_at",
      "media_season",
      "media_series_title",
      "media_title",
      "media_track",
      "repeat",
      "shuffle",
      "sound_mode",
      "sound_mode_list",
      "source",
      "source_list",
      "supported_features",
      "volume_level",
      "volume_step",
    ],
  });

  return <
    PARAMS extends BasicAddParams,
    DATA extends object = CallbackData<
      PARAMS["locals"],
      PARAMS["attributes"],
      MediaPlayerConfiguration<object>
    >,
  >(
    options: AddEntityOptions<
      MediaPlayerConfiguration<DATA>,
      MediaPlayerEvents,
      PARAMS["attributes"],
      PARAMS["locals"],
      DATA
    >,
  ) => {
    // @ts-expect-error it's fine
    return generate.addEntity<PARAMS["attributes"], PARAMS["locals"], DATA>(options);
  };
}
